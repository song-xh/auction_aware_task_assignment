# 2026-04-04 Review

## Scope

This note audits two issues in the current Chengdu-backed experiment path:

1. Why `CAPA` can underperform `RamCOM` in the current `Exp-1` run.
2. Why the Chengdu simulation remains slow even after the preprocessing fixes.

The goal of this document is not to patch the code immediately. The goal is to locate the root causes and give a paper-faithful modification plan.

---

## 1. Current observation

From the current split `Exp-1` run at `|Γ| = 1000`:

- `CAPA`: `TR = 5457.344`, `CR = 0.77`
- `RamCOM`: `TR = 6749.752`, `CR = 1.0`

This is inconsistent with the paper's `Exp-1` and `Exp-4` claims, where `CAPA` should outperform `RamCOM` in `TR`, and for smaller parcel counts should also achieve stronger `CR`.

The gap is not explained by a single bug. It comes from a combination of:

- a non-paper-faithful batch execution flow for `CAPA`
- an overly favorable cooperative environment for `RamCOM`
- aggressive online behavior in the current `RamCOM` adaptation
- repeated expensive shortest-path and insertion computations across all algorithms

---

## 2. Why CAPA is weaker than RamCOM now

### 2.1 The current unified environment is `env/chengdu.py`, but the legacy simulator still drives the core movement and seed generation

The official experiment path is:

- unified environment shell: `env/chengdu.py`
- legacy station and courier seeding: `Framework_ChengDu.GenerateStation`, `Framework_ChengDu.GenerateOriginSchedule`
- legacy movement: `Framework_ChengDu.WalkAlongRoute`

So the project is not directly running `Framework_ChengDu.py` as the top-level experiment script, but it still inherits its courier initialization and movement semantics.

This is fine in principle. The issue is how the unified shell currently exposes tasks and partner platforms to the algorithms.

### 2.2 Partner platforms currently have initial routes, but no continuing task stream

`env/chengdu.py:build_framework_chengdu_environment()` creates one large courier seed pool and then partitions it into:

- `local_couriers`
- `partner_couriers_by_platform`

Those partner couriers are not empty at time zero. They inherit initial `re_schedule` from the legacy seeding process.

However, only the local platform receives the continuing online pick-up stream:

- `tasks = select_station_pick_tasks(...)`

There is no equivalent future task stream for each partner platform.

That means the current environment behaves like this:

- every platform starts with some seeded historical route burden
- only the local platform keeps receiving new pick-up requests
- partner couriers gradually finish their initial routes
- after that, they become almost fully borrowable external capacity for the local platform

This strongly favors cooperative-heavy algorithms, especially `RamCOM`, because its outer-worker branch is evaluated in an environment where partner capacity is increasingly freed for local use instead of being consumed by each partner's own future demand.

This is the most important environment-side fairness gap.

### 2.3 CAPA is not being executed with paper-faithful batch semantics

The paper's Algorithm 1 is batch based:

- accumulate all parcels during the batch window
- when the batch closes, run `CAMA`
- send the rejected set to `DAPA`
- clear the batch state and continue

The current Chengdu runner in `env/chengdu.py:run_time_stepped_chengdu_batches()` does not do that. Inside each batch window it runs:

- a `while cursor < batch_end and unresolved:` loop
- repeated `CAMA`/`DAPA` calls on `arrived_tasks`
- one movement step after each matching attempt

That means the batch is being processed incrementally inside the window instead of once at the batch boundary.

This hurts `CAPA` specifically, because the paper's advantage over `RamCOM` is tied to:

- deferred matching
- threshold-based selection over the whole batch
- pushing lower-utility parcels into cross-platform handling only after the local matching stage sees the batch context

The current runner weakens that mechanism.

### 2.4 The current `step_seconds=60` is larger than the `Exp-1` batch size `30`

`algorithms/capa_runner.py` calls `run_time_stepped_chengdu_batches()` with:

- `batch_seconds = batch_size`
- `step_seconds = 60`

For `Exp-1`, `batch_size = 30`.

So the loop is effectively:

- open a 30-second batch
- process parcels available at the batch start
- advance the environment by 60 seconds
- exit the batch

Parcels that arrive later inside that 30-second bucket are not truly processed within the same batch. They are carried as backlog into the next batch boundary.

This is a real execution mismatch, not just a tuning issue.

For `CAPA`, that means:

- the effective batch content is distorted
- threshold computation is done on an incomplete batch
- some parcels are artificially deferred one extra batch

For `RamCOM`, this distortion does not exist because it runs online per arrival rather than by the batch runner.

This is likely a primary cause of the current `CR` gap.

### 2.5 RamCOM is more aggressive than CAPA in the current adaptation

The current `baselines/ramcom.py` behaves as follows:

- high-value tasks try inner workers first
- otherwise the algorithm builds outer-worker candidates immediately
- if outer candidates exist, it chooses the cooperative payment maximizing expected revenue
- if any outer worker accepts, the task is assigned

By contrast, `CAPA` is more conservative:

- `CAMA` filters local matches using Eq.6 utility and Eq.7 threshold
- unresolved parcels then face DAPA payment-limit filtering
- low-value or high-cost parcels can remain unresolved

This conservatism is correct in the paper, but it only pays off when the environment reflects a real cross-platform market with constrained outer capacity and distinct platform workloads.

In the current environment, outer supply is too generous, so `RamCOM` benefits more than it should.

### 2.6 RamCOM's outer acceptance model is optimistic in the current Chengdu adaptation

The current `RamCOM` adaptation estimates outer-worker acceptance from:

- `history_completed_values` if present
- otherwise the fares of tasks already in the courier's `re_schedule`

Then it aggregates acceptance under an independence assumption.

In the current environment, this creates two optimistic effects:

- outer workers already have history values, so acceptance is never completely cold-start
- because partner platforms lack future own-task pressure, many feasible outer workers remain available to accept

This does not look like a movement bug. It looks like an adaptation that becomes too strong under the current environment.

### 2.7 There is also a shared feasibility simplification that should be fixed, but it is not the main CAPA-vs-RamCOM differentiator

`CAPA`, `RamCOM`, and `MRA` all rely on courier-task feasibility checks that are still simplified relative to the full legacy route semantics.

For example, `legacy_courier_to_capa()` projects a legacy courier into a CAPA snapshot with:

- `current_location`
- `current_load`
- `route_locations`
- `available_from = 0`

The later feasibility checks mostly use:

- current position
- remaining capacity
- deadline to reach the new parcel

They do not fully propagate route timing constraints in the same way as the original legacy insert-and-update routines.

This is important and should be repaired, but it affects multiple algorithms. It does not explain by itself why `RamCOM` beats `CAPA`.

### 2.8 Root-cause judgment

The current `CAPA < RamCOM` result is not strong evidence that the CAPA algorithm is worse.

The more plausible diagnosis is:

1. the environment currently overexposes partner capacity
2. the Chengdu CAPA runner does not execute paper-faithful batch semantics
3. `RamCOM` benefits from a more online and more aggressive cooperative flow

So this result is better interpreted as an experiment-pipeline mismatch than as a genuine algorithmic failure of CAPA.

---

## 3. How the environment flow should change to make the comparison paper-faithful

The goal is not to "help CAPA win" with heuristics. The goal is to restore the environment assumptions that the paper relies on.

### 3.1 Move from one online task stream to multi-platform online task streams

The current environment should be upgraded from:

- one local task stream
- multiple partner courier pools

to:

- one local task stream
- one future task stream per cooperating platform

Each platform should therefore own:

- its own couriers
- its own future parcel arrivals
- its own currently pending local tasks
- its own station/region assignment metadata

This makes partner couriers consume their own platform demand before lending spare capacity outward.

### 3.2 Split each batch into two stages

At each batch boundary:

1. advance the environment to the batch end
2. release newly arrived tasks for every platform
3. let each platform first perform its own local assignment
4. only after that, expose residual partner capacity to cross-platform requests

This is the right place to express "cooperation" instead of letting the local platform treat all partner couriers as immediately borrowable at all times.

### 3.3 Make partner availability residual, not absolute

For DAPA and cross-platform baselines, the candidate partner couriers should be:

- couriers that remain feasible after their own platform processes its own current tasks
- couriers that still satisfy capacity and deadline constraints
- couriers that are currently lendable under the partner platform's residual workload

This directly addresses the current over-supply bias.

### 3.4 Fix CAPA batch execution semantics

The Chengdu CAPA runner should be redesigned so that:

- one batch means one decision epoch
- the full batch parcel set is collected before matching
- `CAMA` and `DAPA` are run once per batch
- movement is decoupled from the matching stage

Movement should still use the legacy road-network logic, but it should happen between batch decisions, not as repeated matching inside one batch.

### 3.5 Decouple movement tick from decision tick

The current `step_seconds = 60` with `batch_size = 30` is structurally inconsistent.

The fix is:

- keep the matching batch duration as the decision window
- let environment advancement operate on smaller event ticks or exact event intervals
- never let movement step size exceed the active decision window

If `batch_size = 30`, then the environment must at least advance to the batch boundary exactly before the batch decision is made.

### 3.6 Preserve one shared environment contract for all algorithms

The environment should expose a standard decision context:

- local platform's current batch tasks
- local couriers after local-state advancement
- partner platforms' residual lendable courier sets
- partner platform prices and cooperation-quality metadata

All algorithms should read from that same context:

- `CAPA`
- `Greedy`
- `BaseGTA`
- `ImpGTA`
- `MRA`
- `RamCOM`

That keeps the comparison fair and prevents one algorithm from receiving a more favorable operational model than another.

---

## 4. Concrete code modification plan for the environment and CAPA fairness issue

### 4.1 Files to change

- `env/chengdu.py`
- `algorithms/capa_runner.py`
- `baselines/ramcom.py`
- `baselines/gta.py`
- `baselines/mra.py`
- `baselines/greedy.py`
- `experiments/seeding.py`
- `experiments/run_exp1_point.py`

### 4.2 Environment refactor plan

In `env/chengdu.py`:

1. add a `PlatformState` data structure containing:
   - `platform_id`
   - `couriers`
   - `future_tasks`
   - `pending_tasks`
   - `station_set` or station ownership metadata
2. change environment construction so pick-up tasks are split into:
   - local platform future tasks
   - one future task stream per partner platform
3. add `advance_to(time)` and `release_tasks(now)` helpers
4. add `build_assignment_context(now, local_platform_id)` returning:
   - local current tasks
   - local couriers
   - partner residual candidate couriers
   - platform metadata

### 4.3 CAPA runner refactor plan

In `algorithms/capa_runner.py` and `env/chengdu.py`:

1. replace the current in-batch repeated matching loop with:
   - accumulate full batch
   - run `CAMA`
   - run `DAPA`
   - write assignments back
   - advance movement to the next batch boundary
2. remove the assumption that `step_seconds` can exceed the batch duration
3. compute batch-level `TR`, `CR`, and `BPT` from one decision epoch per batch

### 4.4 Baseline adaptation plan

In each baseline runner:

1. consume the same environment context object
2. restrict partner couriers to residual lendable sets
3. let partner-platform own-task pressure affect availability
4. keep the revenue formula aligned to the CAPA revenue accounting already implemented

For `RamCOM` specifically:

- use partner platforms' own current/future tasks when deciding lendable outer workers
- keep the payment rule and acceptance model, but do not let the outer pool ignore partner demand

---

## 5. Why the simulation is slow

The current wall-clock bottleneck is not one thing. It is a repeated chain:

`task -> candidate courier -> insertion search -> shortest path`

The slowest part is not just movement. It is the amount of repeated route evaluation inside the assignment algorithms.

### 5.1 Shortest-path calls are the dominant primitive

`capa/experiments.py:ChengduGraphTravelModel.distance()` calls:

- `GraphUtils_ChengDu.g.getShortPath(...)`

`GraphUtils_ChengDu.getShortPath()`:

- constructs an actual path, not just a numeric distance
- scans `openList` linearly to find the minimum score
- reconstructs edge lists and then callers sum lengths

This is much heavier than a distance-only oracle.

### 5.2 Insertion search multiplies shortest-path cost

`capa/utility.py:find_best_local_insertion()` evaluates every insertion point in the route and for each point computes:

- `distance(start, end)`
- `distance(start, parcel)`
- `distance(parcel, end)`

So one courier-task insertion check costs roughly:

- `3 * (route length - 1)` shortest-path queries

This cost is then repeated in many places.

### 5.3 CAPA repeats insertion work across CAMA and DAPA

In `CAPA`:

- `CAMA` computes utility using `find_best_local_insertion()`
- `DAPA` computes FPSA bids through `find_best_auction_detour_ratio()`, which again calls `find_best_local_insertion()`
- after winning DAPA, `apply_cross_assignment()` again calls `find_best_local_insertion()` to obtain the insertion index

So the same courier-task pair can trigger insertion evaluation multiple times in the same decision round.

### 5.4 Baselines repeat the same expensive primitives

`baselines/common.py:build_legacy_feasible_insertions()` already computes:

- feasibility
- best insertion index
- courier-to-task distance

But `MRA` then calls `compute_mra_bid()`, which again calls `find_best_local_insertion()`.

That means `MRA` recomputes the same insertion logic twice for the same edge.

### 5.5 MRA has the heaviest repeated global rebuild

`baselines/mra.py` is especially expensive because it:

- runs multiple rounds over `remaining`
- rebuilds `graph_edges` from scratch each round
- computes feasible insertions for every remaining task against every courier each round
- rescans `graph_edges` to find `best_for_task`

This is algorithmically much heavier than `Greedy` and usually heavier than `RamCOM`.

### 5.6 Legacy movement is not free, but it is not the first bottleneck

`Framework_ChengDu.WalkAlongRoute()` also calls `g.getShortPath()` repeatedly.

However, compared with the assignment stage, movement is a secondary hotspot in the current experiments. The primary time sink is still candidate evaluation during matching.

---

## 6. Concrete speed-up directions

The right optimization principle is:

- do not change the algorithm semantics
- remove duplicate work first
- improve the distance oracle second
- refactor the simulator only after the hot loops are fixed

### 6.1 Stage A: low-risk caching and memoization

#### A1. Add a distance-only shortest-path API

In `GraphUtils_ChengDu.py`:

- add a function that returns shortest-path distance directly instead of reconstructing the full path edge list
- use a heap-based priority queue instead of scanning `openList` linearly

Then update `ChengduGraphTravelModel.distance()` to call the distance-only path when path details are unnecessary.

This should reduce the constant factor of nearly every algorithm.

#### A2. Add insertion-result caching

Introduce a cache keyed by:

- `courier id`
- `route signature`
- `parcel node`

Cache value:

- best detour ratio
- best insertion index

Then reuse it in:

- `CAMA`
- `DAPA`
- `MRA`
- `RamCOM`
- `Greedy`

This removes the largest class of duplicate computation.

#### A3. Cache projected courier snapshots

Legacy-to-CAPA courier projection is repeated throughout the code.

Add a route-state version or signature and cache:

- `legacy courier -> Courier snapshot`

Invalidation only needs to happen when:

- `location` changes
- `re_schedule` changes
- `re_weight` changes

### 6.2 Stage B: algorithm-level pruning

#### B1. Use cheap lower bounds before exact shortest paths

Before running exact road-network distance:

- use straight-line distance or precomputed landmark lower bounds
- reject couriers obviously outside `service_radius`
- reject couriers that obviously miss deadline bounds

Only the surviving candidates need exact `getShortPath()` calls.

#### B2. Build feasible candidate lists once per task-stage

For `CAPA`, `RamCOM`, and `MRA`, the feasible candidate list for one task should be computed once per decision epoch and reused across:

- feasibility
- local utility or bid computation
- final winner application

Do not rebuild equivalent feasible sets separately in different helper calls.

#### B3. Remove duplicate insertion computation inside MRA

In `MRA`:

- store the insertion ratio/index produced by `build_legacy_feasible_insertions()`
- let `compute_mra_bid()` consume that stored information instead of recomputing `find_best_local_insertion()`
- keep per-task best edges in a map instead of rescanning all `graph_edges` repeatedly

This is the most direct `MRA` optimization.

### 6.3 Stage C: simulator and runner refactors

#### C1. Event-driven movement advancement

Instead of repeatedly stepping movement in coarse fixed seconds:

- maintain next waypoint ETA per courier
- advance time directly to the next event boundary

This will reduce repeated `WalkAlongRoute()` calls and repeated route-head shortest-path recomputation.

This is a larger refactor and should come after Stage A and B.

#### C2. Shared batch distance matrices over active nodes

For each decision epoch, collect active nodes:

- courier current locations
- route nodes
- parcel nodes
- stations

Then build a temporary distance cache for the epoch.

This is especially useful when many tasks in the same batch touch the same node set.

### 6.4 Stage D: paper-specific data structures

For `MRA`, the source paper explicitly relies on:

- TS-Tree
- TIL

If the goal is to make `MRA` both faithful and fast, the final optimized path should implement those structures rather than rely on repeated full scans.

---

## 7. Recommended implementation order

### Fairness / CAPA-vs-RamCOM

1. fix batch semantics in `CAPA`
2. decouple movement tick from decision tick
3. add continuing partner-platform task streams
4. restrict partner availability to residual lendable capacity
5. rerun `Exp-1` and `Exp-4`

### Speed

1. add distance-only shortest-path API
2. add insertion caching and courier snapshot caching
3. remove duplicate insertion work in `MRA`
4. add cheap geometric pruning before exact shortest-path queries
5. consider event-driven movement and per-batch active-node distance caches

---

## 8. Bottom line

The current `CAPA < RamCOM` result is more likely caused by the current experiment pipeline than by the CAPA algorithm itself.

The two most important fixes are:

1. make the Chengdu environment multi-platform in terms of future task streams, not only courier pools
2. make the Chengdu CAPA runner obey true batch semantics

The current performance problem is also not one isolated bottleneck. The dominant issue is that exact road-network shortest paths and route insertion evaluation are repeated too many times across all algorithms, with `MRA` being the worst offender.

If these two groups of issues are repaired in that order, the experiments should become both fairer and significantly faster without introducing fallback logic or paper-inconsistent shortcuts.
