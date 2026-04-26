# Review 0426: CAPA Batch Slowdown After Randomized Parcel Sampling

## Scope

This review only audits the current code path. No production code was modified.

Question under review:

- Why does `Exp-1` at `|Gamma|=1000` now show about `100` CAPA batches, while the earlier sequential-prefix logic showed `2` batches?
- Why can the new run feel slower per batch?
- Did the previous graph/caching optimizations stop applying after the sampling logic changed?

## Review Plan

1. Trace the `Exp-1` environment construction path and confirm how the `1000`-parcel point is derived.
2. Compare the time distribution of:
   - old sequential-prefix `1000`,
   - new randomized `1000`,
   - actual `Exp-1` point derivation under canonical seeding.
3. Audit the CAPA runtime path and verify whether these optimizations are still active:
   - Chengdu graph shortest-path cache,
   - persistent distance cache,
   - batch distance matrix,
   - insertion cache,
   - courier snapshot cache,
   - geo shortlist / candidate pruning.
4. Separate:
   - expected slowdown caused by a different parcel time distribution,
   - true optimization regressions or miswired code paths.

## Key Findings

### 1. The jump from `2` batches to about `100` batches is expected under the current `Exp-1` seed derivation

The current `Exp-1 split` path does not independently sample the `1000`-parcel point.

- In [experiments/paper_chengdu.py](/root/code/auction_aware_task_assignment/experiments/paper_chengdu.py:268), the suite first builds one canonical environment for the sweep axis.
- For `num_parcels`, `_canonical_environment_kwargs_for_axis()` uses the maximum point value, not the requested point value. See [experiments/paper_chengdu.py](/root/code/auction_aware_task_assignment/experiments/paper_chengdu.py:832).
- Then `derive_environment_from_seed()` sorts that larger sampled task set by time and takes the prefix `[:num_parcels]`. See [experiments/seeding.py](/root/code/auction_aware_task_assignment/experiments/seeding.py:265).

For the current formal `Exp-1`, this means:

- canonical seed is built at `|Gamma|=5000`,
- the `1000` point is the earliest `1000` tasks inside that `5000`-task random sample,
- not the old “first 1000 tasks in the dataset” behavior.

I verified this with a direct script against the current data path:

- old station-bounded sequential prefix `1000`:
  - `first=0`, `last=41`, `span=41s`
  - `total_batches=2`
  - bucket sizes: `760`, `240`
- current `Exp-1` style derived point:
  - build random `5000`, sort by `s_time`, take earliest `1000`
  - `first=1`, `last=2982`, `span=2981s`
  - `total_batches=100`
  - top bucket sizes: `28`, `22`, `18`, ...
  - average `10` tasks per batch

This exactly matches the observed “`1000` parcels now give about `100` batches”.

Conclusion:

- The batch-count jump is not evidence that the shortest-path cache failed.
- It is a direct consequence of the new random-window plus canonical-seed derivation rule.

### 2. Part of the slowdown is normal wall-clock overhead, even if BPT is unchanged

Batch wall-clock in CAPA is not the same thing as the paper’s `BPT`.

- In [env/chengdu.py](/root/code/auction_aware_task_assignment/env/chengdu.py:1001), `prepare_chengdu_batch()` advances the simulation by one batch window and runs `runtime.movement(...)` before matching.
- In [env/chengdu.py](/root/code/auction_aware_task_assignment/env/chengdu.py:1516), `processing_time_seconds` starts only after batch preparation.

So when parcels are spread across `100` windows instead of `2`:

- the simulator performs far more inter-batch movement calls,
- route states evolve across far more windows,
- terminal progress can look much slower batch-to-batch,
- while the reported `BPT` is still supposed to exclude movement.

Conclusion:

- If the user is observing terminal progress / wall-clock between batch updates, some slowdown is expected and does not by itself imply a metric bug.
- The new sampling logic changes the simulation horizon dramatically, so the runtime profile is no longer comparable to the old “first 1000 tasks in 41 seconds” case.

### 3. The graph-level and cache-level optimizations are still present and active

The core graph/caching stack is still wired in:

- Chengdu road shortest-path cache:
  - `ChengduGraphTravelModel.distance()` uses `@lru_cache(maxsize=200_000)` in [capa/experiments.py](/root/code/auction_aware_task_assignment/capa/experiments.py:61).
- Persistent cross-batch distance cache:
  - `PersistentDirectedDistanceCache` in [capa/utility.py](/root/code/auction_aware_task_assignment/capa/utility.py:220).
  - It is attached to the runtime in `ChengduBatchRuntime.__post_init__`.
- Batch-level distance matrix:
  - `BatchDistanceMatrix` in [capa/utility.py](/root/code/auction_aware_task_assignment/capa/utility.py:271).
  - Local path uses it in [env/chengdu.py](/root/code/auction_aware_task_assignment/env/chengdu.py:1077).
  - Cross path uses it in [env/chengdu.py](/root/code/auction_aware_task_assignment/env/chengdu.py:1295).
- Insertion cache:
  - `InsertionCache` in [capa/utility.py](/root/code/auction_aware_task_assignment/capa/utility.py:79).
  - Pruned and reused per batch in [env/chengdu.py](/root/code/auction_aware_task_assignment/env/chengdu.py:1075) and [env/chengdu.py](/root/code/auction_aware_task_assignment/env/chengdu.py:1293).
- Courier snapshot cache:
  - `LegacyCourierSnapshotCache` is still used to avoid rebuilding courier projections every batch.

Conclusion:

- The main graph-structure optimization is not gone.
- The persistent shortest-path cache and insertion/snapshot caches are still on the hot path.

### 4. But the shortlist-based pruning optimization is currently not aligned with the formal CAPA path

This is the most important audit finding.

The shortlist builders exist:

- local shortlist: [capa/cama.py](/root/code/auction_aware_task_assignment/capa/cama.py:79)
- cross shortlist: [capa/dapa.py](/root/code/auction_aware_task_assignment/capa/dapa.py:84)

Both `run_cama()` and `run_dapa()` already support shortlist inputs:

- `run_cama(..., candidate_couriers_by_parcel=...)` in [capa/cama.py](/root/code/auction_aware_task_assignment/capa/cama.py:151)
- `run_dapa(..., candidate_couriers_by_parcel=...)` in [capa/dapa.py](/root/code/auction_aware_task_assignment/capa/dapa.py:214)

However, the current CAPA mainline does not pass them:

- local path:
  - [env/chengdu.py](/root/code/auction_aware_task_assignment/env/chengdu.py:1519) calls `run_cama(...)` without `candidate_couriers_by_parcel`
- cross path:
  - [env/chengdu.py](/root/code/auction_aware_task_assignment/env/chengdu.py:1297) calls `run_dapa(...)` without `candidate_couriers_by_parcel`

I also confirmed via search that:

- `build_local_candidate_shortlist(...)` currently has no live call site,
- `build_cross_candidate_shortlist(...)` currently has no live call site.

That means the current formal CAPA path does not actually benefit from the intended candidate pruning stage before exact evaluation.

Conclusion:

- This is a real optimization-alignment issue.
- It does not explain the `2 -> 100` batch-count jump.
- But it does mean some of the intended pruning optimization is currently dead code in the formal CAPA experiment path.

### 5. Batch-distance preheating currently happens before any shortlist pruning, so many exact pair lookups are still warmed unnecessarily

In the current local matching runtime:

- [env/chengdu.py](/root/code/auction_aware_task_assignment/env/chengdu.py:1078) runs `distance_matrix.precompute_for_insertions(local_snapshots, batch_parcels)`

This preheat expands over all `courier x parcel` combinations:

- see [capa/utility.py](/root/code/auction_aware_task_assignment/capa/utility.py:312)
- and especially [capa/utility.py](/root/code/auction_aware_task_assignment/capa/utility.py:321)

The same pattern appears in cross matching:

- [env/chengdu.py](/root/code/auction_aware_task_assignment/env/chengdu.py:1296)

Because shortlist pruning is not wired before this step:

- the batch matrix still warms route-insertion pairs for many impossible or irrelevant courier-parcel combinations,
- geo lower-bound pruning is then only applied later, inside the full pair scan in `is_feasible_local_match()` / `is_feasible_cross_match()`,
- so geo pruning still helps correctness and some exact checks, but it does not reduce the preheat loop itself.

Conclusion:

- The batch-distance optimization is active, but it is only partially aligned with the pruning design.
- Current complexity is closer to “warm broadly, prune later” than “prune first, warm only surviving pairs”.

### 6. Later batches in the new run are naturally more expensive because route length grows, and insertion search is route-length sensitive

Insertion search is route-sensitive:

- `find_best_local_insertion()` loops over every route segment in [capa/utility.py](/root/code/auction_aware_task_assignment/capa/utility.py:444)
- `BatchDistanceMatrix.precompute_for_candidate_pairs()` also expands over route segments in [capa/utility.py](/root/code/auction_aware_task_assignment/capa/utility.py:332)

Under the old sequential-prefix `1000`:

- only `2` early windows exist,
- couriers are still near-empty when the two main batches run.

Under the current derived `1000` point:

- there are about `100` windows,
- the experiment spends much longer in the online simulation,
- more assignments are carried across more windows,
- later batches see longer `re_schedule` / route buffers,
- so per-batch insertion work can increase even if each batch has fewer parcels.

Conclusion:

- It is normal for later batches in the new setting to be slower than the old 2-batch early-prefix setting.
- This effect combines with the dead shortlist wiring above.

## Final Judgment

The slowdown is a combination of two factors:

1. Expected behavior from the new task-selection semantics

- `Exp-1` no longer compares against the old “first 1000 tasks” setting.
- It now uses a canonical large sample and derives `1000` as the earliest prefix of that larger random sample.
- That alone changes the time span from about `41s` to about `2981s`, and the batch count from `2` to about `100`.

2. A real optimization alignment issue in CAPA mainline

- shortlist pruning utilities exist but are not connected to the formal CAPA runtime,
- batch distance preheating therefore happens on a broader candidate space than intended,
- so the current runtime does not fully realize the candidate-pruning optimization that the code structure suggests.

## Answer to the Original Question

Is this slowdown “normal”?

- The jump from `2` batches to `100` batches is normal under the new seed-derivation rule.
- Some additional wall-clock slowdown is also normal because movement and route evolution now happen across many more windows.

Did previous optimizations fail completely?

- No. The graph shortest-path cache, persistent distance cache, insertion cache, snapshot cache, and batch distance matrix are still active.

Did some optimizations fail to align with the formal path?

- Yes.
- The shortlist pruning layer is currently not wired into the CAPA mainline, so those candidate-pruning optimizations are not actually used in the formal experiment path.

## Recommended Follow-up

If the goal is to make the new randomized experiment path fast without changing experiment semantics, the first things worth fixing are:

1. Wire `build_local_candidate_shortlist()` into the CAPA local path before calling `run_cama()`.
2. Wire `build_cross_candidate_shortlist()` into the CAPA cross path before calling `run_dapa()`.
3. Change batch-distance preheating to use shortlisted candidate pairs instead of all `courier x parcel` pairs.
4. When comparing runtime, distinguish:
   - wall-clock per online window,
   - matching-only `BPT`,
   - final end-to-end experiment time.
