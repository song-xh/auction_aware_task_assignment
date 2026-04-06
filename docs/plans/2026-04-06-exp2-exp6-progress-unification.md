# Exp2-Exp6 Progress Unification Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make Chengdu paper experiments `Exp-2` through `Exp-6` use the same point/split execution flow and live progress semantics as `Exp-1`.

**Architecture:** Reuse the existing generic experiment framework instead of adding more experiment-specific branches. The main fix is to route every paper experiment axis through the seeded point runner so that point subprocesses always emit `progress.json`, and to make point progress payloads generic over the sweep axis instead of parcel-count-specific.

**Tech Stack:** Python, argparse, Rich live progress, existing `experiments.framework`, Chengdu seeded environment cloning.

---

### Task 1: Plan the point-progress generalization

**Files:**
- Modify: `experiments/progress.py`
- Modify: `experiments/framework/point_runner.py`
- Test: local smoke via `python3 -m unittest`

**Step 1: Define the exact generic point-progress shape**

The point payload should stop assuming `num_parcels` and instead include:

- `axis_name`
- `axis_value`
- `current_algorithm`
- `algorithm_index`
- `total_algorithms`
- `completed_algorithms`
- `state`
- `last_event`

**Step 2: Update the point snapshot builder**

Change `build_point_progress_snapshot()` in `experiments/progress.py` so it accepts `axis_name` and `axis_value` instead of `num_parcels`.

**Step 3: Update the generic point runner**

Change `run_seeded_comparison_point()` in `experiments/framework/point_runner.py` so every point progress write uses:

- `axis_name=point_spec.axis_name`
- `axis_value=point_spec.axis_value`

**Step 4: Verify no parcel-count-only assumption remains**

Search for `num_parcels` inside progress rendering code and confirm the split panel reads the point label from `split_status.json` plus `ExperimentPointSpec`.

**Step 5: Commit**

```bash
git add experiments/progress.py experiments/framework/point_runner.py
git commit -m "refactor(experiments): generalize point progress payloads"
```

### Task 2: Make all paper axes use the seeded point runner

**Files:**
- Modify: `experiments/paper_chengdu.py`
- Modify: `experiments/seeding.py`
- Test: `tests/test_paper_experiments.py`

**Step 1: Add axis-aware environment derivation helpers**

In `experiments/seeding.py`, add reusable helpers that derive one environment from a canonical seed for:

- `num_parcels`
- `local_couriers`
- `service_radius`
- `platforms`
- `courier_capacity`

The derivation must preserve the current experiment semantics:

- no fallback behavior
- no fake tasks
- no algorithm-specific shortcuts

**Step 2: Add canonical-seed builder policy per axis**

In `experiments/paper_chengdu.py`, create one helper that chooses the canonical seed configuration for each axis:

- `num_parcels`: max parcel count
- `local_couriers`: max local courier count
- `platforms`: max platform count
- `courier_capacity`: default fixed config is fine
- `service_radius`: default fixed config is fine

This helper must build a seed large enough that later point derivation is valid for every formal point.

**Step 3: Route `run_chengdu_paper_point()` through the seeded point runner for every axis**

Remove the special-case that only `num_parcels` uses `run_seeded_comparison_point()`. Instead:

- load or build canonical seed
- derive one point environment with the axis-aware derivation helper
- run all algorithms through `run_seeded_comparison_point()`

**Step 4: Route `run_chengdu_paper_split_experiment()` through the same seeded point logic**

Ensure the split subprocess command continues to use `--execution-mode point`, but now every point mode shares the same seeded path and progress writing behavior.

**Step 5: Commit**

```bash
git add experiments/paper_chengdu.py experiments/seeding.py
git commit -m "feat(experiments): unify seeded point execution across paper axes"
```

### Task 3: Align startup/live progress semantics with Exp-1

**Files:**
- Modify: `experiments/framework/split_runner.py`
- Modify: `experiments/framework/point_runner.py`
- Modify: `experiments/progress.py`
- Test: `tests/test_experiment_progress.py`

**Step 1: Add an explicit launcher/startup phase**

Before point subprocesses begin algorithm execution, make sure the point runner writes a first `progress.json` snapshot with:

- `phase = "starting"`
- `detail = "starting <algorithm>"`

This already exists in the generic point runner; verify the split panel surfaces it for non-Exp-1 axes too.

**Step 2: Make the split status block semantically consistent**

Confirm the split panel always shows:

- experiment label (`Exp-2`, `Exp-3`, ...)
- axis label (`|C|`, `rad`, `|P|`, `cap`)
- current algorithm index and name
- current phase and detail from point progress

If any field defaults to `0/6:-` while a valid point progress file exists, fix the merge logic in `collect_split_progress()` / `build_split_progress_renderable()`.

**Step 3: Keep overwrite-style live rendering**

Do not change the current Rich live rendering architecture; only ensure the non-Exp-1 flows now feed it correctly.

**Step 4: Commit**

```bash
git add experiments/framework/split_runner.py experiments/framework/point_runner.py experiments/progress.py
git commit -m "fix(experiments): align paper split progress semantics"
```

### Task 4: Add tests that cover Exp2-Exp6 parity with Exp-1

**Files:**
- Modify: `tests/test_paper_experiments.py`
- Modify: `tests/test_experiment_progress.py`

**Step 1: Add a failing test for non-Exp-1 point mode**

Write a test that exercises `run_chengdu_paper_point(axis="local_couriers", ...)` and asserts:

- `progress.json` is written
- the payload contains `axis_name="local_couriers"`
- the payload contains an algorithm start/completion sequence

**Step 2: Add a failing test for non-Exp-1 split aggregation**

Write a test for `run_chengdu_paper_split_experiment(axis="local_couriers", ...)` with a fake runner that emits progress callbacks. Assert:

- split progress snapshot contains `current_algorithm`
- `algorithm_index` is non-zero once work starts
- point rows no longer stay at `0/6:-`

**Step 3: Add a test for axis labels in the Rich/text renderers**

Verify:

- `local_couriers -> |C|`
- `service_radius -> rad`
- `platforms -> |P|`
- `courier_capacity -> cap`

**Step 4: Commit**

```bash
git add tests/test_paper_experiments.py tests/test_experiment_progress.py
git commit -m "test(experiments): cover non-exp1 progress parity"
```

### Task 5: Verify with targeted smoke runs

**Files:**
- No code changes required

**Step 1: Run focused tests**

Run:

```bash
python3 -m unittest tests.test_paper_experiments tests.test_experiment_progress -v
```

Expected:

- PASS
- no progress regression for Exp-1
- non-Exp-1 axes now emit progress payloads

**Step 2: Run Exp-2 split smoke**

Run:

```bash
python3 experiments/run_chengdu_exp2_couriers.py \
  --execution-mode split \
  --tmp-root /tmp/chengdu_exp2_progress_smoke \
  --output-dir /tmp/chengdu_exp2_progress_smoke_out \
  --preset smoke \
  --algorithms capa greedy \
  --poll-seconds 1
```

Expected:

- split panel shows non-empty algorithm and phase information
- point directories contain `progress.json`
- output summary is produced

**Step 3: Run one more non-Exp-1 point smoke**

Run:

```bash
python3 experiments/run_chengdu_exp3_radius.py \
  --execution-mode point \
  --point-value 1.0 \
  --output-dir /tmp/chengdu_exp3_point_progress_smoke \
  --algorithms capa greedy
```

Expected:

- point `summary.json` exists
- point `progress.json` exists

**Step 4: Commit**

```bash
git add -A
git commit -m "fix(experiments): unify exp2-exp6 flow with exp1 progress"
```
