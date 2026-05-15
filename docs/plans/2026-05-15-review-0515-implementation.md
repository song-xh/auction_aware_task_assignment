# Review 0515 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement the fixes requested in `docs/review_0515.md`, continuing from the partially completed deadline and RamCOM work already present in the working tree.

**Architecture:** Keep settlement, deadline handling, CAMA decision logic, and plotting changes isolated by module. Preserve shared CAPA modules as the single path used by CAPA and RL-CAPA, and do not add fallback logic.

**Tech Stack:** Python, pytest, existing CAPA/RL-CAPA modules, Chengdu experiment runners.

---

### Task 1: Record Current Progress

**Files:**
- Create: `docs/plans/2026-05-15-review-0515-implementation.md`

**Steps:**
1. Inspect existing diffs for RamCOM, deadline, CAMA, and plotting work.
2. Record the execution plan and commit the plan only.
3. Verify with `git status --short` that only the intended plan file is staged for this commit.

**Commit:** `docs: plan review 0515 implementation`

### Task 2: RamCOM Cross Settlement Diagnostics

**Files:**
- Modify: `baselines/ramcom.py`
- Modify: `tests/test_metric_alignment.py`

**Steps:**
1. Run `pytest tests/test_metric_alignment.py -k "ramcom or gta" -v` to capture current status.
2. Keep delivered-only cross diagnostics: `cross_payment_total`, `cross_fare_total`, `avg_cross_payment_ratio`, `cross_local_revenue_total`.
3. Ensure RamCOM final cross settlement uses a CAPA-aligned platform payment floor.
4. Re-run `pytest tests/test_metric_alignment.py -k "ramcom or gta" -v`.

**Commit:** `fix(ramcom): align cross settlement diagnostics`

### Task 3: Deadline Parameterization

**Files:**
- Modify: `capa/config.py`
- Modify: `env/chengdu.py`
- Modify: `experiments/config.py`
- Modify: `experiments/paper_chengdu.py`
- Modify: `experiments/sweep.py`
- Modify: `tests/test_deadline_disturbance.py`

**Steps:**
1. Run `pytest tests/test_deadline_disturbance.py -v` to capture current status.
2. Ensure `deadline_seconds` is stored in experiment config, CLI fixed config, manifest fields, and environment kwargs.
3. Ensure Chengdu task loading rewrites dataset deadlines as `s_time + deadline_seconds` while preserving the raw value for audit.
4. Re-run `pytest tests/test_deadline_disturbance.py -v`.

**Commit:** `feat(env): parameterize chengdu deadlines`

### Task 4: Revenue-Based CAMA Threshold

**Files:**
- Modify: `capa/utility.py`
- Modify: `capa/models.py`
- Modify: `capa/cama.py`
- Modify: `tests/test_capa_local.py`

**Steps:**
1. Run `pytest tests/test_capa_local.py -v` and confirm the new revenue-threshold tests fail before implementation.
2. Add local revenue score and threshold helpers.
3. Update `ThresholdHistory` to accumulate feasible-pair local revenue scores.
4. Update `run_cama()` to choose primary local candidates and threshold decisions by local revenue score, using existing utility/insertion only for deterministic tie-break and route insertion.
5. Re-run `pytest tests/test_capa_local.py -v`.

**Commit:** `fix(cama): use local revenue threshold`

### Task 5: Plot Filtering and BPT Label

**Files:**
- Modify: `experiments/plotting.py`
- Test: `tests/test_plotting.py`

**Steps:**
1. Run `pytest tests/test_plotting.py -v` and confirm plotting expectations fail before implementation.
2. Change BPT label to `Batch Process Time`.
3. Add `visible_algorithms_for_metric()` and apply it to comparison and default comparison plots.
4. Re-run `pytest tests/test_plotting.py -v`.

**Commit:** `fix(plot): filter comparison baselines`

### Task 6: Review Result Notes and Regression

**Files:**
- Create or modify: `docs/review_0515_result.md`

**Steps:**
1. Run targeted regression:
   - `pytest tests/test_metric_alignment.py -k "ramcom or gta" -v`
   - `pytest tests/test_deadline_disturbance.py -v`
   - `pytest tests/test_capa_local.py -v`
   - `pytest tests/test_plotting.py -v`
2. Record implemented changes, test evidence, and any deferred formal experiment reruns.
3. Commit the result notes.

**Commit:** `docs: summarize review 0515 fixes`
