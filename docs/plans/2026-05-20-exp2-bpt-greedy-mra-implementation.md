# Exp2 BPT And Baseline Tuning Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Align Exp-2 baseline `BPT` with the paper-style matching-runtime contract, expose fair paper-runner parameter propagation, and retune the Exp-2 NY environment so `greedy` and `mra` no longer have abnormally low `CR`.

**Architecture:** Keep baseline matching policies unchanged, but widen their reported runtime from decision-only timing to full matching-epoch elapsed time. Use the paper experiment runner as the single place where shared revenue/tuning parameters are forwarded, then perform smoke retuning on the fixed Exp-2 environment before running the full NY sweep.

**Tech Stack:** Python 3, pytest, unified Chengdu/NY paper experiment runner, existing baseline adapters.

---

### Task 1: Lock The New Baseline BPT Contract In Tests

**Files:**
- Modify: `tests/test_metric_alignment.py`
- Modify: `tests/test_mra_bpt.py`

**Step 1: Write the failing test**

Add tests that assert:
- `greedy`, `basegta`, `impgta`, and `ramcom` report full per-decision elapsed time, including routing / insertion work
- `mra` reports full per-round elapsed time, including graph construction and insertion work
- old decision-only expectations no longer hold

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_metric_alignment.py tests/test_mra_bpt.py -q`

Expected: FAIL because the current runners still subtract routing / insertion work from reported `BPT`.

**Step 3: Write minimal implementation**

Change baseline timing accumulation to use full matching-epoch elapsed time rather than the currently reduced decision-only delta.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_metric_alignment.py tests/test_mra_bpt.py -q`

Expected: PASS.

### Task 2: Forward Shared Revenue Controls Through The Paper Runner

**Files:**
- Modify: `experiments/paper_chengdu.py`
- Modify: `tests/test_metric_alignment.py`

**Step 1: Write the failing test**

Add tests that assert `build_paper_runner_overrides_from_fixed_config()` forwards:
- `local_payment_ratio_zeta`
- `local_sharing_rate_mu1`
- `cross_platform_sharing_rate_mu2`
- optional `max_outer_payment_ratio` for `ramcom` if present

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_metric_alignment.py -q`

Expected: FAIL because the current function only forwards ImpGTA prediction controls and RL controls.

**Step 3: Write minimal implementation**

Extend `build_paper_runner_overrides_from_fixed_config()` so the paper point/split runner forwards shared revenue parameters to every algorithm that consumes them.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_metric_alignment.py -q`

Expected: PASS.

### Task 3: Verify The Paper Runner Still Builds Correct Summaries

**Files:**
- Modify: `tests/test_plotting.py` only if metric filtering assumptions break
- Optional Modify: `algorithms/summary_utils.py` only if summary output needs extra audit fields

**Step 1: Run focused regression tests**

Run: `pytest tests/test_plotting.py tests/test_algorithm_summary_fields.py -q`

Expected: PASS or only targeted, directly explainable failures.

**Step 2: Fix only if the BPT contract change breaks the public summary shape**

Do not refactor unrelated plotting or summary code.

### Task 4: Run Small Exp-2 Smoke Sweeps To Retune CR And TR

**Files:**
- No code file required unless a real bug is found

**Step 1: Run a small smoke around the current command**

Use reduced `num_parcels` first, then sweep:
- `deadline_seconds`
- `service_radius_km`
- `batch_size`
- `prediction_window_seconds`
- `prediction_success_rate`
- `local_payment_ratio_zeta`
- `cross_platform_sharing_rate_mu2`

**Step 2: Evaluate against explicit acceptance checks**

Check:
- `BPT` is no longer near zero for `greedy` / `ramcom` / `basegta`
- `BPT` rises with courier count
- `TR` keeps `ramcom > mra > greedy`
- `CR` for `greedy` and `mra` is materially higher than the current `result/exp2_ny_couriers_d600`

**Step 3: Pick the best formal configuration**

Favor the smallest parameter changes that satisfy the trend goals.

### Task 5: Run The Full NY Exp-2 Sweep

**Files:**
- Modify result artifacts under the user-chosen output directory

**Step 1: Run the full `split` experiment**

Use the tuned command derived from Task 4.

**Step 2: Inspect the generated `summary.json`**

Verify:
- `BPT` monotonic trend is sensible
- `TR` ordering holds
- `CR` is no longer abnormally low for `greedy` / `mra`

### Task 6: Final Verification

**Files:**
- No code file required

**Step 1: Run fresh verification commands**

Run the exact focused test commands used for Tasks 1-3, then inspect the full Exp-2 output summary again.

**Step 2: Report with evidence**

Include:
- the code changes
- the tuned command
- the resulting metric trends
- any remaining tradeoffs if a perfect ordering cannot be achieved without changing baseline semantics
