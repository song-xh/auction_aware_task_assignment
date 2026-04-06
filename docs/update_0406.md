# 2026-04-06 Update Plan

## Scope

This document records a code-change plan only. It does not modify runtime code.

Goals:

1. Reduce the main CAPA complexity drivers at large `|Γ|`, especially repeated retry recomputation and route-growth cost.
2. Generalize `experiments/run_exp1_split.py`, `experiments/run_exp1_point.py`, and `experiments/run_exp1_managed.py` into a reusable experiment framework rather than an Exp-1-only stack.
3. Simplify the `capa/` helper layout by folding small generic helpers such as `capa/revenue.py` and `capa/travel.py` into `capa/utility.py`, then updating old imports.

This plan is based on the current paper-faithful Chengdu environment and the current long-running Exp-1 behavior:

- `5000` parcels enter multiple backlog retries because `run_time_stepped_chengdu_batches()` continues matching while `backlog` remains non-empty.
- Each retry currently reconstructs snapshots, insertion caches, and batch distance caches from scratch.
- Courier routes grow over time, so later insertion search becomes more expensive even when backlog size shrinks.

## Problem 1: CAPA Large-Scale Complexity

### Root Cause Summary

The main complexity is not a single function. It is the product of:

- `retry_rounds`
- `eligible/backlog parcels in the round`
- `local_couriers` and `partner couriers`
- route segment count per courier
- repeated shortest-path lookups during insertion search

The main hot path is:

1. [env/chengdu.py](/root/code/auction_aware_task_assignment/env/chengdu.py)
   `run_time_stepped_chengdu_batches()`
2. [capa/cama.py](/root/code/auction_aware_task_assignment/capa/cama.py)
   `run_cama()`
3. [capa/utility.py](/root/code/auction_aware_task_assignment/capa/utility.py)
   `find_best_local_insertion()`
4. [capa/dapa.py](/root/code/auction_aware_task_assignment/capa/dapa.py)
   `run_dapa()`
5. [capa/batch_distance.py](/root/code/auction_aware_task_assignment/capa/batch_distance.py)
   `precompute_for_insertions()`

### Why Current Optimizations Are Not Enough

Current optimizations help within one matching round:

- geometric lower-bound pruning
- batch distance precompute
- insertion cache

But they do not persist across retry rounds because the following objects are recreated every round inside `run_time_stepped_chengdu_batches()`:

- `TimingAccumulator`
- `TimedTravelModel`
- `LegacyCourierSnapshotCache`
- `InsertionCache`
- `BatchDistanceMatrix`

This means the code reduces repeated work within a single round but still pays most of the cost again in `retry 1`, `retry 2`, ..., `retry k`.

### Modification Order

The order below is chosen to target the dominant complexity first.

#### Step A1: Add Cross-Round Route-Versioned Caches

Primary files:

- [env/chengdu.py](/root/code/auction_aware_task_assignment/env/chengdu.py)
- [capa/cache.py](/root/code/auction_aware_task_assignment/capa/cache.py)
- [capa/utility.py](/root/code/auction_aware_task_assignment/capa/utility.py)
- [capa/batch_distance.py](/root/code/auction_aware_task_assignment/capa/batch_distance.py)

Current logic to change:

- In `run_time_stepped_chengdu_batches()`, cache objects are created inside the while-loop.
- Insertion cache keys use `(courier_id, route_signature, parcel_location)`, but the cache only lives for one round.

Planned changes:

1. Move persistent caches outside the main while-loop in `run_time_stepped_chengdu_batches()`.
2. Add a route version mechanism for each legacy courier.
3. Extend `InsertionCache` to use:
   - `courier_id`
   - `route_version`
   - `parcel_location`
4. Keep cache entries valid across rounds until a courier route actually changes.
5. Add a persistent directed distance cache layer that survives retries and is invalidated only when necessary, not every round.

Expected effect:

- Retry rounds reuse prior insertion results for unchanged couriers.
- Repeated backlog rounds stop recomputing the same `(courier, parcel)` insertion over and over.

#### Step A2: Add Explicit Courier Route Mutation Tracking

Primary files:

- [env/chengdu.py](/root/code/auction_aware_task_assignment/env/chengdu.py)
- [baselines/common.py](/root/code/auction_aware_task_assignment/baselines/common.py)

Current logic to change:

- `apply_assignment_to_legacy_courier()` mutates `re_schedule` and `re_weight`, but does not emit any version/invalidation metadata.

Planned changes:

1. Add a monotonically increasing route-version field on legacy couriers when a task is inserted.
2. Increment route version inside:
   - `apply_assignment_to_legacy_courier()`
   - any other route mutation helper used by baselines
3. Use this route version as the invalidation boundary for all route-based caches.

Expected effect:

- Cache invalidation becomes exact.
- Only couriers touched by the last round lose cached insertion results.

#### Step A3: Short-Circuit Terminal Backlog Earlier

Primary files:

- [env/chengdu.py](/root/code/auction_aware_task_assignment/env/chengdu.py)
- [capa/constraints.py](/root/code/auction_aware_task_assignment/capa/constraints.py)

Current logic to change:

- After each round, any task not assigned and not expired goes back into `backlog`.
- There is only one terminal shortcut now:
  - no assignments
  - last arrival window reached
  - no pending legacy routes

Planned changes:

1. Add a stronger terminal infeasibility filter before reinserting into backlog.
2. For each unresolved task, compute whether it is impossible for all candidate couriers under lower-bound checks:
   - deadline lower bound
   - service radius lower bound
   - capacity impossibility
3. Move such tasks directly to `terminal_unassigned`.

Expected effect:

- Retry count drops because hopeless tasks stop circulating.

#### Step A4: Replace Full Courier Scan With Candidate Shortlisting

Primary files:

- [capa/cama.py](/root/code/auction_aware_task_assignment/capa/cama.py)
- [capa/dapa.py](/root/code/auction_aware_task_assignment/capa/dapa.py)
- [capa/constraints.py](/root/code/auction_aware_task_assignment/capa/constraints.py)
- [capa/utility.py](/root/code/auction_aware_task_assignment/capa/utility.py)

Current logic to change:

- `run_cama()` scans every local courier for every parcel.
- `run_dapa()` scans every partner courier in every platform for every parcel.

Planned changes:

1. Add a cheap candidate ranking stage using only low-cost signals:
   - Haversine lower bound
   - current load ratio
   - available time
   - route length proxy
2. Keep only top-k local couriers per parcel before exact utility evaluation.
3. Keep only top-k partner couriers per platform before exact auction bid evaluation.
4. Make `k` configurable through CAPA config or environment extra config.

Expected effect:

- The exact insertion search runs on a small candidate subset instead of the full courier pool.

#### Step A5: Add Route-Segment Pruning in Insertion Search

Primary files:

- [capa/utility.py](/root/code/auction_aware_task_assignment/capa/utility.py)
- [capa/batch_distance.py](/root/code/auction_aware_task_assignment/capa/batch_distance.py)

Current logic to change:

- `find_best_local_insertion()` scans all route segments.
- Every segment receives exact distance queries.

Planned changes:

1. Introduce a two-stage insertion scan:
   - stage 1: cheap lower-bound estimate per segment
   - stage 2: exact shortest-path evaluation only for promising segments
2. Carry a current best score and skip segments whose lower bound cannot beat it.
3. Optionally restrict exact scan to a bounded number of candidate segments.

Expected effect:

- Route growth hurts less because later route segments are pruned without exact distance calls.

#### Step A6: Delay or Narrow DAPA Admission

Primary files:

- [capa/cama.py](/root/code/auction_aware_task_assignment/capa/cama.py)
- [capa/dapa.py](/root/code/auction_aware_task_assignment/capa/dapa.py)
- [env/chengdu.py](/root/code/auction_aware_task_assignment/env/chengdu.py)

Current logic to change:

- Every local-unmatched parcel directly enters DAPA.

Planned changes:

1. Add a DAPA admission policy for backlog-heavy batches:
   - high fare
   - tight deadline
   - utility close to threshold
2. Lower-priority parcels remain in backlog instead of paying cross-platform evaluation immediately.

Expected effect:

- Partner-side exact evaluation cost is reduced in large windows and deep retry rounds.

## Problem 2: Experiment Framework Is Too Exp-1-Specific

### Root Cause Summary

Current files:

- [experiments/run_exp1_point.py](/root/code/auction_aware_task_assignment/experiments/run_exp1_point.py)
- [experiments/run_exp1_split.py](/root/code/auction_aware_task_assignment/experiments/run_exp1_split.py)
- [experiments/run_exp1_managed.py](/root/code/auction_aware_task_assignment/experiments/run_exp1_managed.py)

These files implement reusable concepts, but they are hard-coded as Exp-1:

- point execution
- split-process orchestration
- managed multi-round retry
- progress files
- point summary promotion

At the same time, the repository already has partially generic layers:

- [experiments/sweep.py](/root/code/auction_aware_task_assignment/experiments/sweep.py)
- [experiments/compare.py](/root/code/auction_aware_task_assignment/experiments/compare.py)
- [experiments/progress.py](/root/code/auction_aware_task_assignment/experiments/progress.py)
- [experiments/seeding.py](/root/code/auction_aware_task_assignment/experiments/seeding.py)

The right direction is not to keep adding `run_expX_*` stacks, but to extract a generic orchestration framework and make Exp-1 one configuration of that framework.

### Planned Refactor

#### Step B1: Introduce Generic Experiment Entities

New target files:

- `experiments/framework/models.py`
- `experiments/framework/specs.py`

Introduce generic data types:

- `ExperimentPointSpec`
- `ExperimentSuiteSpec`
- `ManagedRoundSpec`
- `ExperimentRuntimeState`

These should describe:

- axis name and values
- fixed environment config
- algorithms
- per-algorithm runner kwargs
- temporary output layout
- promotion/finalization policy

#### Step B2: Extract Point Runner From Exp-1

Current source:

- [experiments/run_exp1_point.py](/root/code/auction_aware_task_assignment/experiments/run_exp1_point.py)

New target:

- `experiments/framework/point_runner.py`

Move generic logic out of Exp-1:

- load canonical seed
- derive point environment
- clone environment per algorithm
- write point-level progress
- persist point `summary.json`

Leave Exp-1-specific logic only as configuration:

- the `num_parcels` axis
- CAPA override arguments

#### Step B3: Extract Split Launcher From Exp-1

Current source:

- [experiments/run_exp1_split.py](/root/code/auction_aware_task_assignment/experiments/run_exp1_split.py)

New target:

- `experiments/framework/split_runner.py`

Move generic logic out of Exp-1:

- canonical seed creation
- one-process-per-point launch
- point directory reset
- launcher status file
- progress rendering
- final result aggregation

Refactor so Exp-1 only supplies:

- point values
- suite metadata
- plotting function
- optional CAPA round overrides

#### Step B4: Extract Managed Multi-Round Controller

Current source:

- [experiments/run_exp1_managed.py](/root/code/auction_aware_task_assignment/experiments/run_exp1_managed.py)

New target:

- `experiments/framework/managed_runner.py`

Move generic logic out of Exp-1:

- multi-round loop
- round directories
- round manifest writing
- status writing
- winner promotion

Keep experiment-specific pieces injectable:

- round scoring function
- acceptance threshold
- parameter override set
- next-round recommendation logic

#### Step B5: Rebuild Exp-1 As Thin Wrappers

After extraction, the existing files should become thin compatibility entrypoints:

- [experiments/run_exp1_point.py](/root/code/auction_aware_task_assignment/experiments/run_exp1_point.py)
- [experiments/run_exp1_split.py](/root/code/auction_aware_task_assignment/experiments/run_exp1_split.py)
- [experiments/run_exp1_managed.py](/root/code/auction_aware_task_assignment/experiments/run_exp1_managed.py)

Each wrapper should:

- assemble Exp-1 spec
- call generic framework entrypoints

This keeps CLI stability while removing duplication.

#### Step B6: Reuse the Framework For Other Experiments

Targets to adopt the framework later:

- paper Exp-2 / Exp-3 / Exp-4 / Exp-5 wrappers
- baseline-only sweeps
- RL-CAPA train/eval experiment bundles

This step is intentionally later. The first refactor should only make framework extraction possible and keep existing CLIs working.

## Problem 3: CAPA Helper Layout Is Too Fragmented

### Root Cause Summary

The helper logic is currently spread across:

- [capa/utility.py](/root/code/auction_aware_task_assignment/capa/utility.py)
- [capa/revenue.py](/root/code/auction_aware_task_assignment/capa/revenue.py)
- [capa/travel.py](/root/code/auction_aware_task_assignment/capa/travel.py)

`revenue.py` and `travel.py` are both small, but have many imports across:

- `capa/cama.py`
- `capa/dapa.py`
- `capa/runner.py`
- `baselines/greedy.py`
- `baselines/gta.py`
- `baselines/mra.py`
- `baselines/ramcom.py`
- `capa/__init__.py`

The user-requested direction is to fold these generic helpers into `capa/utility.py`.

### Planned Refactor

#### Step C1: Expand `capa/utility.py` Into the Canonical Helper Hub

Primary file:

- [capa/utility.py](/root/code/auction_aware_task_assignment/capa/utility.py)

Add three sections:

1. travel helper section
   - move `DistanceMatrixTravelModel` from `travel.py`
2. revenue helper section
   - move payment and revenue functions from `revenue.py`
3. insertion and utility section
   - keep current route/insertion/threshold logic

The file should then become the single “small helper” entrypoint for:

- distance abstraction
- payment/revenue helpers
- insertion and utility helpers

#### Step C2: Update Old Imports

Files requiring import rewrites:

- [capa/cama.py](/root/code/auction_aware_task_assignment/capa/cama.py)
- [capa/dapa.py](/root/code/auction_aware_task_assignment/capa/dapa.py)
- [capa/runner.py](/root/code/auction_aware_task_assignment/capa/runner.py)
- [capa/__init__.py](/root/code/auction_aware_task_assignment/capa/__init__.py)
- [baselines/greedy.py](/root/code/auction_aware_task_assignment/baselines/greedy.py)
- [baselines/gta.py](/root/code/auction_aware_task_assignment/baselines/gta.py)
- [baselines/mra.py](/root/code/auction_aware_task_assignment/baselines/mra.py)
- [baselines/ramcom.py](/root/code/auction_aware_task_assignment/baselines/ramcom.py)

The rewrite rule should be:

- from `capa.revenue` -> `capa.utility`
- from `capa.travel` -> `capa.utility`

#### Step C3: Keep Compatibility Shims Temporarily

To avoid a large blast radius in one commit:

- keep `capa/revenue.py`
- keep `capa/travel.py`

but reduce them to compatibility re-exports during an intermediate phase.

That enables:

1. internal import migration first
2. tests and runners verification
3. optional deletion later

This is safer than deleting both modules immediately.

## Recommended Execution Order

The recommended implementation order is:

1. Extract experiment framework entities and point/split/managed runners.
2. Convert Exp-1 wrappers to the new framework.
3. Consolidate `capa/revenue.py` and `capa/travel.py` into `capa/utility.py` with compatibility shims.
4. Introduce route-versioned persistent caches across retry rounds.
5. Add route mutation tracking.
6. Add terminal backlog pruning.
7. Add courier shortlist generation.
8. Add route-segment pruning in insertion search.
9. Narrow DAPA admission for backlog-heavy rounds.

This ordering minimizes risk:

- framework refactor is mostly organizational
- helper consolidation is local and low-risk
- complexity reductions then build on a cleaner base

## Test and Verification Plan

When implementation starts, verification should be staged as follows.

### Experiment Framework

Add tests for:

- generic point runner summary generation
- generic split runner process status and final aggregation
- generic managed runner round promotion and round scoring hooks
- Exp-1 compatibility wrappers still producing the same output structure

### CAPA Helper Consolidation

Add tests for:

- imports through `capa.utility`
- compatibility re-exports from `capa.revenue` and `capa.travel`
- unchanged revenue values and travel behavior

### Complexity Optimizations

Add tests for:

- cache reuse across retry rounds
- route-version invalidation after assignment writeback
- terminal pruning removes impossible backlog tasks
- shortlist logic still preserves known feasible winners on small deterministic cases
- insertion pruning does not change results on deterministic synthetic cases

### Performance Verification

Use a small but meaningful Chengdu profile run and track:

- retry count
- repeated distance calls
- repeated insertion calls
- wall time per CAPA round

The first success criterion is not “instant fast.” It is:

- fewer retry rounds
- fewer exact insertion evaluations
- lower repeated distance lookup volume
- materially faster `5000`-point CAPA first-algorithm wall time

## Non-Goals For The First Refactor

The following should not be mixed into the same implementation batch:

- changing the paper reward/revenue definitions
- redesigning the multi-platform task-flow fairness issue
- changing RL-CAPA interfaces
- altering experiment metrics or output JSON schema more than necessary

These are separate concerns and should stay out of the first cleanup/performance refactor.
