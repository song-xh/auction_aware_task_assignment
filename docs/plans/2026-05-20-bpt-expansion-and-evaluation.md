# BPT Expansion And Evaluation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Expand BPT from decision-only timing to a fuller batch-runtime metric that better reflects graph preparation, insertion search, routing, matching, and batch movement overhead, then verify the new metric behaves more realistically.

**Architecture:** Keep the existing timing breakdown fields intact, but change the aggregate BPT definition to use a per-batch accounted runtime helper shared by CAPA, RL-CAPA, and plotting. Prefer explicit helper functions over ad-hoc sums so summaries, evaluation, and per-batch curves stay aligned.

**Tech Stack:** Python, pytest, CAPA timing helpers, Chengdu runtime, RL-CAPA evaluation and plotting.

---

### Task 1: Define The New BPT Contract In Tests

**Files:**
- Modify: `tests/test_metric_alignment.py`
- Modify: `tests/test_rl_env_smoke.py`
- Create or Modify: `tests/test_bpt_accounting.py`

**Step 1: Write the failing test**

Add tests that assert:
- batch-level accounted BPT includes `processing_time_seconds` plus movement time when present
- fallback behavior still works when only timing breakdown exists
- aggregate `compute_batch_processing_time()` uses the new per-batch helper
- RL-CAPA evaluation still matches `compute_batch_processing_time(env.batch_reports())`

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_metric_alignment.py tests/test_rl_env_smoke.py tests/test_bpt_accounting.py -q`

Expected: FAIL because current code still uses `decision_time_seconds` only.

**Step 3: Keep tests minimal**

Use synthetic `BatchReport` values so the failure isolates the aggregation bug rather than simulator noise.

### Task 2: Implement Shared Batch-Time Accounting

**Files:**
- Modify: `capa/metrics.py`
- Modify: `capa/models.py` if docstrings need clarification

**Step 1: Add a per-batch helper**

Implement a helper that computes one batch’s accounted BPT using:
- `processing_time_seconds` as the matching/runtime wall-clock core
- `movement_time_seconds` as extra batch runtime outside the matching window
- fallback to timing components when `processing_time_seconds` is zero or absent

**Step 2: Update aggregate BPT**

Make `compute_batch_processing_time()` average the new per-batch accounted time, not `decision_time_seconds`.

**Step 3: Keep timing breakdown fields**

Do not remove `excluded_routing_time`, `excluded_insertion_time`, or `excluded_movement_time`; preserve auditability while widening BPT.

### Task 3: Align CAPA And RL-CAPA Batch Plots

**Files:**
- Modify: `capa/experiments.py`
- Modify: `rl_capa/visualize.py`

**Step 1: Replace decision-only batch BPT series**

Use the shared per-batch helper for `bpt_over_batches.png` generation in both CAPA and RL-CAPA.

**Step 2: Preserve labels**

Keep plot labels as `BPT`, but ensure the underlying values now reflect the new aggregation so batch curves show realistic variation.

### Task 4: Verify On Targeted Evaluation

**Files:**
- No code file required unless diagnostics are needed

**Step 1: Run focused tests**

Run: `pytest tests/test_metric_alignment.py tests/test_rl_env_smoke.py tests/test_bpt_accounting.py -q`

Expected: PASS.

**Step 2: Run a small workload evaluation**

Run a focused script or existing evaluation path to inspect whether:
- BPT is materially larger than decision-only tens of milliseconds
- BPT changes with workload size instead of staying flat

**Step 3: Sanity-check no interface regressions**

Run the existing plotting/timing-related tests if touched:

Run: `pytest tests/test_plotting.py -q`

Expected: PASS.
