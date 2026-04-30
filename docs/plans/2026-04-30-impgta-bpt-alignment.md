# ImpGTA and BPT Alignment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Repair ImpGTA prediction-threshold behavior under the CPUL courier-capacity model and align reported BPT units across CAPA and baselines.

**Architecture:** Keep each algorithm's assignment policy intact, but fix shared evaluation semantics. ImpGTA will translate future supply from "number of workers" to "available capacity slots" because one courier can carry multiple parcels in this repository's CPUL simulator. BPT will be reported as mean assignment-decision time per matching decision epoch, with routing, insertion, and movement excluded as before.

**Tech Stack:** Python 3, `unittest`, existing CAPA/GTA baseline modules.

---

### Task 1: Fix ImpGTA supply-demand threshold for CPUL capacity

**Files:**
- Modify: `baselines/gta.py`
- Test: `tests/test_metric_alignment.py`

**Step 1:** Write failing tests for `count_available_capacity_slots()` and for ImpGTA accepting a feasible local task when residual courier capacity exceeds predicted future tasks.

**Step 2:** Run `python3 -m unittest tests.test_metric_alignment -v` and verify the new tests fail.

**Step 3:** Add `count_available_capacity_slots()` and use it in ImpGTA inner/outer prediction-threshold call sites instead of raw available-courier count.

**Step 4:** Run `python3 -m unittest tests.test_metric_alignment -v` and verify PASS.

**Step 5:** Commit `fix(impgta): use courier capacity for prediction thresholds`.

---

### Task 2: Correct ImpGTA outer threshold decision value

**Files:**
- Modify: `baselines/gta.py`
- Test: `tests/test_metric_alignment.py`

**Step 1:** Write a failing test where an outer platform has insufficient future capacity, dispatch cost is below the future expected reward, but estimated current cooperative payment exceeds the future expected reward.

**Step 2:** Run `python3 -m unittest tests.test_metric_alignment -v` and verify the test fails under the current dispatch-cost comparison.

**Step 3:** Add `estimate_impgta_outer_task_value()` and compare that estimated current payment/reward with `expected_future_reward()`.

**Step 4:** Run `python3 -m unittest tests.test_metric_alignment -v` and verify PASS.

**Step 5:** Commit `fix(impgta): compare predicted demand with estimated cross reward`.

---

### Task 3: Align BPT units across algorithms

**Files:**
- Modify: `capa/metrics.py`
- Modify: `baselines/greedy.py`
- Modify: `baselines/gta.py`
- Modify: `baselines/mra.py`
- Modify: `baselines/ramcom.py`
- Test: `tests/test_metric_alignment.py`
- Test: `tests/test_mra_bpt.py`
- Test: `tests/test_rl_env_smoke.py`

**Step 1:** Write failing tests that assert `compute_batch_processing_time()` and baseline BPT return mean assignment-decision time per decision epoch.

**Step 2:** Run `python3 -m unittest tests.test_metric_alignment tests.test_mra_bpt tests.test_rl_env_smoke -v` and verify failure.

**Step 3:** Change CAPA metrics and baselines to divide decision-time accumulators by matching decision epoch count, while preserving the existing exclusion of routing, insertion, and movement time.

**Step 4:** Run `python3 -m unittest tests.test_metric_alignment tests.test_mra_bpt tests.test_rl_env_smoke -v` and verify PASS.

**Step 5:** Commit `fix(metrics): report mean assignment bpt across algorithms`.

---

### Task 4: Validate with small Chengdu smoke comparisons

**Step 1:** Run `python3 -m unittest tests.test_metric_alignment tests.test_mra_bpt tests.test_rl_env_smoke -v`.

**Step 2:** Run a small `runner.py compare` smoke with `capa basegta impgta greedy ramcom`, 80 parcels, Chengdu data, and the same prediction/window/history parameters used by the formal experiments.

**Step 3:** Run `python3 -m unittest discover -s tests -v`.

**Step 4:** Commit only if the smoke exposes and fixes additional code/test updates.
