# Deadline-Accurate Delivery Accounting Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Repair Chengdu CAPA, RL-CAPA, and baseline metric accounting so `TR` and `CR` count only parcels actually delivered on time under the true deadline, while accepted-but-late parcels are removed as `timeout` failures.

**Architecture:** Introduce one shared delivery-outcome tracking layer in the Chengdu route progression path. Every accepted task must end in exactly one terminal state: `delivered_on_time`, `timed_out_after_acceptance`, or `terminal_unassigned_before_acceptance`. All metric builders and experiment summaries must derive `TR`/`CR` from the on-time-delivered set only, while keeping accepted counts and timeout counts as separate diagnostic fields.

**Tech Stack:** Python 3, legacy Chengdu simulator (`Framework_ChengDu.py`), shared Chengdu runtime (`env/chengdu.py`), CAPA metric models (`capa/models.py`, `capa/metrics.py`), baseline adapters, pytest/unittest.

---

## Current Review

### Root Cause 1: CAPA and RL-CAPA currently collapse `accepted` into `delivered`

**Evidence**

- [env/chengdu.py](/home/sxh/code/auction/auction_aware_task_assignment/env/chengdu.py:1545) `finalize_chengdu_runtime()` drains routes and then returns `[assignment.parcel for assignment in runtime.matching_plan]`.
- [env/chengdu.py](/home/sxh/code/auction/auction_aware_task_assignment/env/chengdu.py:1764) `run_time_stepped_chengdu_batches()` uses that return value as `delivered_parcels`.
- [capa/metrics.py](/home/sxh/code/auction/auction_aware_task_assignment/capa/metrics.py:10) `compute_total_revenue(assignments)` sums every accepted assignment revenue.
- [rl_capa/env.py](/home/sxh/code/auction/auction_aware_task_assignment/rl_capa/env.py:359) RL finalization also assigns `self._delivered_parcels = finalize_chengdu_runtime(runtime)`.
- [rl_capa/evaluate_core.py](/home/sxh/code/auction/auction_aware_task_assignment/rl_capa/evaluate_core.py:95) RL evaluation computes `total_revenue = sum(a.local_platform_revenue for a in accepted)`.

**Impact**

- CAPA `TR` is currently based on accepted assignments, not verified on-time deliveries.
- CAPA/RL `delivered_parcels` is effectively “everything ever accepted,” not “everything actually completed before deadline.”
- Any accepted parcel that should fail after acceptance can still inflate `TR` and `CR`.

### Root Cause 2: Legacy route progression removes tasks without deadline outcome classification

**Evidence**

- [Framework_ChengDu.py](/home/sxh/code/auction/auction_aware_task_assignment/Framework_ChengDu.py:271) `WalkAlongRoute()` pops `courier.re_schedule[0]` when the courier reaches it.
- The same function does not emit `completed_at`, `deadline`, or `timeout` status.
- [env/chengdu.py](/home/sxh/code/auction/auction_aware_task_assignment/env/chengdu.py:903) `compute_delivered_legacy_task_ids()` infers delivery from “no longer present in any route.”

**Impact**

- A parcel removed from route is treated as delivered even if the actual service time is later than the true deadline.
- There is currently no explicit `timeout` bucket for accepted-but-late tasks.

### Root Cause 3: Batch waiting time is already part of simulated time and must be preserved

**Evidence**

- [env/chengdu.py](/home/sxh/code/auction/auction_aware_task_assignment/env/chengdu.py:1128) `prepare_chengdu_batch()` advances `runtime.current_time` by `batch_seconds`.
- Backlog tasks are carried into later batches via `input_tasks = [*runtime.backlog, *arrived_tasks]`.
- Eligibility is tested against the updated absolute `runtime.current_time`.

**Conclusion**

- A parcel released at 9:00 and matched four batches later is already being evaluated at the later absolute time.
- The fix must preserve this behavior.
- No special “extra wait penalty” should be added separately; the correct approach is to compare the actual absolute completion time against the true deadline.

### Root Cause 4: Baselines use delivered-only revenue, but “delivered” still means route disappearance

**Evidence**

- [baselines/common.py](/home/sxh/code/auction/auction_aware_task_assignment/baselines/common.py:33) `sum_delivered_assignment_revenue()` is already delivered-only.
- But Greedy, GTA, MRA, and RamCOM all derive `delivered_task_ids` through [compute_delivered_legacy_task_ids](/home/sxh/code/auction/auction_aware_task_assignment/env/chengdu.py:903), which still treats route disappearance as success.

**Impact**

- Baseline `TR` is narrower than old “accepted revenue,” but still not deadline-accurate.
- Baseline `CR` still overcounts late deliveries as successful completions.

### Root Cause 5: Unified summaries do not expose timeout as a first-class failure state

**Evidence**

- [algorithms/summary_utils.py](/home/sxh/code/auction/auction_aware_task_assignment/algorithms/summary_utils.py:42) only builds `local_matches`, `cross_platform_matches`, and `unresolved_parcels`.
- No runner or result schema currently exposes `timed_out_parcels`.

**Impact**

- Experiment outputs cannot distinguish:
  - never accepted,
  - accepted but timed out,
  - successfully delivered on time.

---

## Required Behavioral Invariants

After the fix, the codebase must satisfy all of the following:

1. Every task ends in exactly one terminal state:
   - `delivered_on_time`
   - `timed_out_after_acceptance`
   - `terminal_unassigned_before_acceptance`
2. `TR` is the sum of local-platform revenue over `delivered_on_time` assignments only.
3. `CR` is `delivered_on_time / total_tasks`.
4. `accepted_assignments` remains a separate diagnostic count and must not imply delivery success.
5. `timed_out_parcels` must be counted explicitly and must not contribute to `TR` or `CR`.
6. Success/failure must be judged against the true deadline `d_time`, not `observed_d_time`.
7. Batch waiting time must remain part of the absolute completion time because `runtime.current_time` already accumulates inter-batch waiting.

---

## Non-Goals For This Change

- Do **not** redesign the CAPA/RL-CAPA reward functions yet.
- Do **not** introduce fallback heuristics.
- Do **not** silently reinterpret the paper.
- Do **not** change parcel generation, sampling, or Exp-7/8 disturbance semantics.
- Do **not** bundle unrelated optimization work.

---

### Task 1: Lock Down Deadline-Accurate Delivery Semantics With Failing Tests

**Files:**
- Create: `tests/test_deadline_delivery_accounting.py`
- Modify: `tests/test_metric_alignment.py`
- Modify: `tests/test_algorithm_summary_fields.py`
- Modify: `tests/test_rl_env_smoke.py`

**Step 1: Write the failing shared-environment tests**

Add tests that express the intended semantics before touching implementation.

```python
def test_on_time_delivery_counts_as_delivered_and_revenue() -> None:
    result = run_time_stepped_chengdu_batches(...)
    assert result.metrics.delivered_parcel_count == 1
    assert result.metrics.timed_out_parcel_count == 0
    assert result.metrics.total_revenue == expected_revenue


def test_accepted_but_late_delivery_becomes_timeout() -> None:
    result = run_time_stepped_chengdu_batches(...)
    assert result.metrics.accepted_parcel_count == 1
    assert result.metrics.delivered_parcel_count == 0
    assert result.metrics.timed_out_parcel_count == 1
    assert result.metrics.total_revenue == 0.0


def test_batch_waiting_time_counts_toward_true_completion_time() -> None:
    result = run_time_stepped_chengdu_batches(...)
    assert result.metrics.accepted_parcel_count == 1
    assert result.metrics.timed_out_parcel_count == 1
```

**Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/test_deadline_delivery_accounting.py -v
```

Expected:

- Fail because `RunMetrics` does not yet expose timeout counts.
- Fail because CAPA still counts accepted assignments as delivered/revenue.

**Step 3: Add failing runner/summary tests**

Extend summary tests so every algorithm summary must expose timeout counts explicitly.

```python
assert summary["metrics"]["timed_out_parcels"] == 1
assert summary["assignment_stats"]["local_platform"]["timed_out_parcels"] == 1
```

**Step 4: Run the focused summary tests**

Run:

```bash
pytest tests/test_algorithm_summary_fields.py -v
```

Expected:

- Fail because current summary payload does not include timeout fields.

**Step 5: Commit the failing-test scaffold**

```bash
git add tests/test_deadline_delivery_accounting.py tests/test_metric_alignment.py tests/test_algorithm_summary_fields.py tests/test_rl_env_smoke.py
git commit -m "test: add failing deadline-accurate delivery accounting coverage"
```

---

### Task 2: Introduce Explicit Delivery Outcomes in The Shared Chengdu Runtime

**Files:**
- Modify: `Framework_ChengDu.py`
- Modify: `env/chengdu.py`
- Modify: `capa/models.py`

**Step 1: Add explicit shared delivery outcome models**

Define the minimal shared types needed by every algorithm.

```python
@dataclass(frozen=True)
class DeliveryOutcome:
    task_id: str
    completed_at: float
    deadline: float
    on_time: bool


@dataclass(frozen=True)
class BatchReport:
    ...
    delivered_parcel_count: int = 0
    timed_out_parcel_count: int = 0


@dataclass(frozen=True)
class RunMetrics:
    ...
    delivered_parcel_count: int = 0
    accepted_parcel_count: int = 0
    timed_out_parcel_count: int = 0
```

**Step 2: Extend legacy route advancement to emit completion events**

Update `Framework_ChengDu.WalkAlongRoute()` so it can optionally append delivery events while preserving existing route movement semantics.

```python
def WalkAlongRoute(..., delivery_events=None, absolute_time=None):
    ...
    completed_at = absolute_time + time_cost
    if delivery_events is not None:
        delivery_events.append(
            {
                "task_id": str(courier.re_schedule[0].num),
                "completed_at": completed_at,
                "deadline": float(courier.re_schedule[0].d_time),
            }
        )
```

Do **not** add fallback branches. Make the event emission explicit and deterministic.

**Step 3: Add one shared wrapper in `env/chengdu.py` that classifies outcomes**

Create one helper that:

- advances all active routes for one interval,
- collects completion events,
- classifies each event with `completed_at <= get_true_deadline(task)`,
- updates runtime-level `delivered` and `timeout` sets.

```python
def advance_routes_with_deadline_accounting(
    runtime: ChengduBatchRuntime,
    step_seconds: int,
) -> list[DeliveryOutcome]:
    ...
```

`completed_at` must be absolute simulation time, so batch waiting remains part of the final service time.

**Step 4: Replace “route disappearance == delivered” in the CAPA runtime**

Stop using:

- `compute_delivered_legacy_task_ids()` as the primary success criterion
- `finalize_chengdu_runtime()` returning every accepted parcel

Instead, keep explicit runtime state:

```python
accepted_assignment_ids: set[str]
delivered_assignment_ids: set[str]
timed_out_assignment_ids: set[str]
delivery_outcomes: list[DeliveryOutcome]
```

**Step 5: Commit the runtime-model change**

```bash
git add Framework_ChengDu.py env/chengdu.py capa/models.py
git commit -m "feat(env): add explicit deadline-aware delivery outcomes"
```

---

### Task 3: Rebuild CAPA And RL-CAPA Metrics On Top Of On-Time Delivery Only

**Files:**
- Modify: `env/chengdu.py`
- Modify: `capa/metrics.py`
- Modify: `algorithms/capa_runner.py`
- Modify: `rl_capa/env.py`
- Modify: `rl_capa/evaluate_core.py`
- Modify: `rl_capa/evaluate.py`

**Step 1: Make CAPA finalization return true on-time deliveries**

Replace the current “all accepted assignments after draining” finalizer with one that returns on-time-delivered assignments/parcels only.

```python
def finalize_chengdu_runtime(runtime: ChengduBatchRuntime) -> tuple[list[Assignment], list[Assignment]]:
    delivered_assignments = [...]
    timed_out_assignments = [...]
    return delivered_assignments, timed_out_assignments
```

The exact return type can differ, but the finalizer must expose both success and timeout outputs explicitly.

**Step 2: Make `build_run_metrics()` revenue-delivery aware**

Change metric assembly so `TR` no longer accepts a raw accepted-assignment list.

```python
def build_run_metrics(
    delivered_assignments: Sequence[Assignment],
    total_parcels: int,
    batch_reports: Sequence[BatchReport],
    *,
    accepted_parcel_count: int,
    timed_out_parcel_count: int,
) -> RunMetrics:
    return RunMetrics(
        total_revenue=compute_total_revenue(delivered_assignments),
        completion_rate=len(delivered_assignments) / total_parcels,
        ...
    )
```

**Step 3: Fix RL evaluation to stop summing accepted revenue**

`rl_capa/evaluate_core.py` must derive evaluation `TR` from on-time-delivered assignments, not from `env.accepted_assignments()`.

```python
delivered_assignments = env.delivered_assignments()
total_revenue = sum(a.local_platform_revenue for a in delivered_assignments)
completion_rate = len(delivered_assignments) / max(total_parcels, 1)
```

If `RLCAPAEnv` does not yet expose `delivered_assignments()`, add that API.

**Step 4: Run focused CAPA/RL tests**

Run:

```bash
pytest tests/test_deadline_delivery_accounting.py tests/test_rl_env_smoke.py tests/test_rl_output_artifacts.py -v
```

Expected:

- CAPA and RL tests pass with delivered-only accounting.
- Any remaining failures should be due to missing baseline updates, not CAPA/RL logic.

**Step 5: Commit the CAPA/RL metric repair**

```bash
git add env/chengdu.py capa/metrics.py algorithms/capa_runner.py rl_capa/env.py rl_capa/evaluate_core.py rl_capa/evaluate.py
git commit -m "fix(metrics): base capa and rl-capa revenue on on-time deliveries"
```

---

### Task 4: Apply The Same On-Time Delivery Accounting To Greedy, GTA, MRA, And RamCOM

**Files:**
- Modify: `baselines/common.py`
- Modify: `baselines/greedy.py`
- Modify: `baselines/gta.py`
- Modify: `baselines/mra.py`
- Modify: `baselines/ramcom.py`
- Modify: `algorithms/basegta_runner.py`
- Modify: `algorithms/greedy_runner.py`
- Modify: `algorithms/impgta_runner.py`
- Modify: `algorithms/mra_runner.py`
- Modify: `algorithms/ramcom_runner.py`
- Modify: `algorithms/summary_utils.py`

**Step 1: Replace route-disappearance success inference with explicit delivery outcomes**

Introduce a shared baseline helper that consumes accepted-task revenue and explicit outcome IDs:

```python
def summarize_deadline_aware_outcomes(
    accepted_revenues_by_task_id: Mapping[str, float],
    delivered_task_ids: Iterable[str],
    timed_out_task_ids: Iterable[str],
) -> tuple[float, int, int]:
    ...
```

Do **not** keep `compute_delivered_legacy_task_ids()` as the success oracle.

**Step 2: Update every baseline result payload**

Each baseline summary dict should now carry:

```python
{
    "TR": ...,
    "CR": ...,
    "BPT": ...,
    "delivered_parcels": delivered_count,
    "accepted_assignments": accepted_count,
    "timed_out_parcels": timed_out_count,
}
```

**Step 3: Update unified summary construction**

`build_algorithm_summary()` must expose timeout explicitly.

```python
"assignment_stats": {
    "local_platform": {
        "local_matches": ...,
        "cross_platform_matches": ...,
        "timed_out_parcels": timed_out_count,
        "unresolved_parcels": unresolved_count,
    },
}
```

`unresolved_parcels` must remain “not successfully completed,” but timeout must not be hidden inside that bucket.

**Step 4: Run baseline-focused regression tests**

Run:

```bash
pytest tests/test_metric_alignment.py tests/test_algorithm_summary_fields.py -v
```

Expected:

- Existing metric-alignment tests pass after updating expectations.
- New timeout-specific assertions pass for Greedy/GTA/MRA/RamCOM.

**Step 5: Commit the baseline accounting alignment**

```bash
git add baselines/common.py baselines/greedy.py baselines/gta.py baselines/mra.py baselines/ramcom.py algorithms/basegta_runner.py algorithms/greedy_runner.py algorithms/impgta_runner.py algorithms/mra_runner.py algorithms/ramcom_runner.py algorithms/summary_utils.py
git commit -m "fix(baselines): count revenue and completion from on-time deliveries only"
```

---

### Task 5: Verify End-To-End Experiment Semantics And Freeze The New Contract

**Files:**
- Modify: `tests/test_metric_alignment.py`
- Modify: `tests/test_algorithm_summary_fields.py`
- Modify: `tests/test_rl_env_smoke.py`
- Modify: `README.md` only if current metric wording becomes incorrect

**Step 1: Add contract tests for the new terminal-state partition**

Add one compact invariant test:

```python
assert (
    delivered_parcels
    + timed_out_parcels
    + unresolved_before_acceptance
) == total_tasks
```

Use both CAPA and one baseline fixture.

**Step 2: Run the full targeted regression suite**

Run:

```bash
pytest \
  tests/test_deadline_delivery_accounting.py \
  tests/test_metric_alignment.py \
  tests/test_algorithm_summary_fields.py \
  tests/test_rl_env_smoke.py \
  tests/test_rl_output_artifacts.py -v
```

Expected:

- All targeted tests pass.
- No remaining assertion still treats `accepted_assignments` as delivered success.

**Step 3: Run one small real experiment smoke**

Run:

```bash
python3 -u experiments/run_chengdu_exp5_default_compare.py \
  --output-dir /tmp/exp5_deadline_accounting_smoke \
  --algorithms capa greedy basegta impgta mra ramcom \
  --data-dir Data \
  --num-parcels 50 \
  --local-couriers 10 \
  --platforms 2 \
  --couriers-per-platform 5 \
  --courier-capacity 25 \
  --service-radius-km 1.0 \
  --batch-size 30 \
  --prediction-window-seconds 30
```

Check:

- `summary.json` includes `timed_out_parcels`
- `TR` decreases when timeouts exist
- `CR` uses on-time delivered count only

**Step 4: Update any stale metric wording**

If README or docstrings still claim “assigned” or “route-removed” instead of “on-time delivered,” update them in the same change set.

**Step 5: Commit the verified contract**

```bash
git add tests/test_deadline_delivery_accounting.py tests/test_metric_alignment.py tests/test_algorithm_summary_fields.py tests/test_rl_env_smoke.py tests/test_rl_output_artifacts.py README.md
git commit -m "docs: document deadline-accurate delivery accounting contract"
```

---

## Implementation Checkpoints

The implementation is correct only if every checkpoint below passes:

1. **Accepted-vs-delivered separation**
   - One accepted parcel can end with `accepted_assignments=1`, `delivered_parcels=0`, `timed_out_parcels=1`.

2. **Batch waiting is preserved**
   - A backlog parcel that waits across multiple batches uses the later absolute `current_time` when judged for final service success.

3. **True deadline wins**
   - Exp-8 observed/noisy deadline may affect decision-making, but final success/failure is still compared against `d_time`.

4. **No timeout revenue leakage**
   - A timed-out accepted parcel contributes `0` to `TR`.

5. **No timeout completion leakage**
   - A timed-out accepted parcel contributes `0` to `CR`.

6. **Unified semantics**
   - CAPA, RL-CAPA, Greedy, BaseGTA, ImpGTA, MRA, and RamCOM all follow the same terminal-state contract.

7. **Summary visibility**
   - Output JSON exposes `accepted_assignments`, `delivered_parcels`, and `timed_out_parcels` separately.

---

## Expected End State

After executing this plan:

- `TR` will become strictly smaller whenever accepted tasks are delivered late.
- `CR` will become stricter because only on-time completions count.
- The current “accepted but eventually popped from route” overcount will disappear.
- Large-batch settings with backlog pressure will show more realistic degradation.
- Exp-7/Exp-8 robustness results will become interpretable, because deadline pressure will affect both decision-making and final success accounting consistently.

---

## Notes For The Implementer

- Preserve the current absolute-time semantics. Do not add a second waiting-time penalty on top of `runtime.current_time`.
- Keep the change centered around one shared delivery-outcome mechanism. Do not duplicate deadline-finalization logic per algorithm.
- Resist the urge to “also improve” matching heuristics in the same patch. First make accounting correct; only then consider route-level pre-accept deadline tightening as a separate follow-up.
