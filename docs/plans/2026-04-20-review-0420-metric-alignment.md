# Review 0420 Metric Alignment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Repair baseline metric accounting so CAPA, Greedy, MRA, RamCOM, BaseGTA, and ImpGTA all report TR/CR/BPT under one unified CPUL evaluation protocol, while also cleaning the broken `env/chengdu.py` mainline metrics flow.

**Architecture:** Keep each method's decision mechanism unchanged, but route all result accounting through the same delivered-based completion semantics, Eq.5-style local-platform revenue rules, and decision-time-only BPT boundary. Fix `env/chengdu.py` first because its current merge-conflict state makes the runtime and metrics chain unverifiable.

**Tech Stack:** Python, unified Chengdu environment, CAPA metric models, local unittest/py_compile verification.

---

### Task 1: Lock down the current failures with tests

**Files:**
- Modify: `tests/test_baseline_runner.py`
- Modify: `tests/test_mra_ramcom.py`
- Create: `tests/test_metric_alignment.py`
- Test: `tests/test_metric_alignment.py`

**Step 1: Write failing tests for metric alignment**

Add tests that prove:
- BaseGTA/ImpGTA cross assignments use `fare - AIM second_lowest_payment`
- BaseGTA/ImpGTA/Greedy/MRA/RamCOM report `CR` from delivered parcels, not accepted count
- Baseline `BPT` excludes movement/routing/insertion time
- `env/chengdu.py` can be imported/compiled without conflict markers

**Step 2: Run the targeted tests to verify they fail**

Run:
```bash
python3 -m unittest tests.test_metric_alignment -v
python3 -m py_compile env/chengdu.py
```

Expected:
- at least one FAIL in metric assertions
- `py_compile` fails on `env/chengdu.py` due to conflict markers

**Step 3: Commit the failing-test checkpoint**

```bash
git add tests/test_metric_alignment.py tests/test_baseline_runner.py tests/test_mra_ramcom.py docs/plans/2026-04-20-review-0420-metric-alignment.md
git commit -m "test(metrics): add failing alignment coverage for baselines"
```

### Task 2: Repair `env/chengdu.py` runtime and metric chain

**Files:**
- Modify: `env/chengdu.py`
- Test: `tests/test_metric_alignment.py`

**Step 1: Resolve the merge-conflict region in `run_time_stepped_chengdu_batches()`**

Keep the shared-helper path:
- `build_chengdu_local_matching_runtime(...)`
- `commit_chengdu_local_assignments(...)`
- `run_chengdu_cross_matching(...)`

Delete the stale inline branch.

**Step 2: Re-check delivered-based metric accounting**

Verify and preserve:
- `finalize_chengdu_batch()` sets `BatchReport.delivered_parcel_count` from accepted-minus-active-route ids
- `finalize_chengdu_runtime()` drains accepted routes and returns delivered parcels
- final `CAPAResult.metrics` uses `build_run_metrics(..., delivered_parcel_count=len(delivered_parcels))`

**Step 3: Run tests**

Run:
```bash
python3 -m py_compile env/chengdu.py
python3 -m unittest tests.test_metric_alignment -v
```

Expected: green on env compilation and env-related metric tests.

**Step 4: Commit**

```bash
git add env/chengdu.py tests/test_metric_alignment.py
git commit -m "fix(env): restore unified chengdu batch metrics flow"
```

### Task 3: Align BaseGTA and ImpGTA metrics with CAPA

**Files:**
- Modify: `baselines/gta.py`
- Test: `tests/test_metric_alignment.py`
- Test: `tests/test_baseline_runner.py`

**Step 1: Keep AIM and dispatch logic unchanged**

Do not change:
- local-first dispatch
- platform-level AIM winner/payment
- ImpGTA future-window participation logic

**Step 2: Fix unified metrics**

Adjust the runner so that:
- `TR` remains unified via `compute_local_platform_revenue_for_local_completion()` / `compute_local_platform_revenue_for_cross_completion()`
- `delivered_parcels` is computed after final drain from actual route completion, not `accepted_assignments`
- `CR = delivered_parcels / total_task_count`
- `BPT` remains decision-time only
- optional native GTA stats, if any, stay auxiliary and not primary metrics

**Step 3: Run tests**

Run:
```bash
python3 -m unittest tests.test_metric_alignment tests.test_baseline_runner -v
```

**Step 4: Commit**

```bash
git add baselines/gta.py tests/test_metric_alignment.py tests/test_baseline_runner.py
git commit -m "fix(gta): align basegta and impgta metrics with capa"
```

### Task 4: Align Greedy, MRA, and RamCOM delivered/processing metrics

**Files:**
- Modify: `baselines/greedy.py`
- Modify: `baselines/mra.py`
- Modify: `baselines/ramcom.py`
- Test: `tests/test_metric_alignment.py`
- Test: `tests/test_mra_ramcom.py`

**Step 1: Preserve method logic**

Do not alter matching rules. Only adjust metric finalization:
- delivered count after drain
- `CR` from delivered count
- `TR` from unified revenue helpers only
- `BPT` from decision-time-only window

**Step 2: Run tests**

Run:
```bash
python3 -m unittest tests.test_metric_alignment tests.test_mra_ramcom -v
```

**Step 3: Commit**

```bash
git add baselines/greedy.py baselines/mra.py baselines/ramcom.py tests/test_metric_alignment.py tests/test_mra_ramcom.py
git commit -m "fix(baselines): align delivered completion and bpt metrics"
```

### Task 5: Full verification for unified metric surface

**Files:**
- Modify if needed: `algorithms/*runner.py`
- Modify if needed: `experiments/*`
- Test: existing baseline and experiment tests

**Step 1: Verify runner surface consistency**

Confirm no algorithm wrapper rewrites baseline metric keys or uses alternative accounting.

**Step 2: Run final verification matrix**

Run:
```bash
python3 -m py_compile env/chengdu.py baselines/common.py baselines/greedy.py baselines/mra.py baselines/ramcom.py baselines/gta.py capa/metrics.py algorithms/basegta_runner.py algorithms/impgta_runner.py algorithms/greedy_runner.py algorithms/mra_runner.py algorithms/ramcom_runner.py
python3 -m unittest tests.test_metric_alignment tests.test_baseline_runner tests.test_mra_ramcom -v
python3 tests/test_full_pipeline.py
```

**Step 3: Commit final integration polish if any code changed**

```bash
git add <files>
git commit -m "test(metrics): verify unified baseline evaluation surface"
```
