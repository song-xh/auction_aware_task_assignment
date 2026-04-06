# 2026-04-06 Update 0406 Execution Plan

## Objective

Implement the actionable parts of [update_0406.md](/root/code/auction_aware_task_assignment/docs/update_0406.md) while preserving experiment semantics.

This execution explicitly excludes any change that alters CAPA's search space or paper-defined decision flow.

## In-Scope

1. Extract a reusable experiment framework from:
   - `experiments/run_exp1_point.py`
   - `experiments/run_exp1_split.py`
   - `experiments/run_exp1_managed.py`
2. Consolidate small CAPA helper modules into `capa/utility.py`
   while keeping compatibility shims for old imports.
3. Implement semantics-preserving performance improvements:
   - persistent cross-round caches
   - route-version invalidation
   - exact terminal backlog pruning
   - exact insertion pruning based on safe lower bounds

## Out of Scope

These ideas from `update_0406.md` will not be implemented in this batch because they change the algorithm search space or matching policy:

1. top-k courier shortlisting
2. DAPA admission narrowing / delayed auction filtering

Those are optimization ideas, not semantics-preserving refactors.

## Implementation Order

### Step 1

Build generic experiment framework modules:

- `experiments/framework/models.py`
- `experiments/framework/point_runner.py`
- `experiments/framework/split_runner.py`
- `experiments/framework/managed_runner.py`

Then refit `run_exp1_point.py`, `run_exp1_split.py`, and `run_exp1_managed.py`
into thin wrappers around the framework.

### Step 2

Merge `capa/revenue.py` and `capa/travel.py` into `capa/utility.py`, then reduce:

- `capa/revenue.py`
- `capa/travel.py`

to compatibility re-export modules.

Update internal imports across CAPA and baselines.

### Step 3

Add cross-round route-aware caches:

- persistent insertion cache
- persistent directed distance cache
- route-version tracking on legacy couriers

Primary files:

- `env/chengdu.py`
- `capa/cache.py`
- `capa/batch_distance.py`
- `capa/utility.py`

### Step 4

Add exact terminal backlog pruning in `env/chengdu.py`.

The rule must remain semantics-preserving:
only prune tasks proven infeasible for all candidate couriers under exact or admissible lower-bound checks.

### Step 5

Add exact insertion pruning in `capa/utility.py`.

This must not change the chosen insertion result; it may only skip segment evaluations that are provably unable to beat the current best score.

## Verification Strategy

1. Add focused tests before each implementation slice.
2. Run targeted tests after each slice.
3. Run full suite before any final integration claim.
4. Do not commit final results without verification.

## Commit Plan

1. `docs(plan): add update_0406 execution plan`
2. `refactor(experiments): extract reusable experiment framework`
3. `refactor(capa): consolidate utility revenue and travel helpers`
4. `feat(cache): persist cross-round route-aware caches`
5. `fix(env): prune terminal backlog with exact infeasibility checks`
6. `feat(capa): add semantics-preserving insertion pruning`

