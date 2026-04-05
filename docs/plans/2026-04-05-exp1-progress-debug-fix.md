# Exp1 Progress Debug Fix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix Exp-1 terminal progress so it overwrites in place, uses correct terminology, and shows meaningful intra-batch progress on small and formal runs.

**Architecture:** Keep the existing split-process experiment structure, but separate terminal rendering concerns from point progress persistence. Clarify top-level progress as point-algorithm runs, then add finer-grained CAPA parcel progress from `CAMA`/`DAPA` so a long first batch still advances visibly.

**Tech Stack:** Python, unittest, existing Chengdu environment and CAPA modules.

---

### Task 1: Add failing progress rendering and CAPA intra-batch tests

**Files:**
- Modify: `tests/test_experiment_progress.py`
- Modify: `tests/test_chengdu_runner.py`
- Modify: `tests/test_paper_experiments.py`

**Step 1: Write the failing tests**

- Add a test asserting formatted split output uses `algorithm_runs` wording and per-point `algo=i/n`.
- Add a test asserting terminal render helper prefixes ANSI clear-screen codes when overwrite mode is enabled.
- Add a test asserting `run_time_stepped_chengdu_batches()` can emit parcel-level CAPA progress events such as `cama_parcel_progress`.

**Step 2: Run tests to verify they fail**

Run:

```bash
python3 -m unittest tests.test_experiment_progress tests.test_chengdu_runner tests.test_paper_experiments -v
```

Expected: FAIL because overwrite rendering and intra-batch CAPA progress do not exist yet.

**Step 3: Commit**

```bash
git add tests/test_experiment_progress.py tests/test_chengdu_runner.py tests/test_paper_experiments.py
git commit -m "test(experiments): cover exp1 progress overwrite and intra-batch updates"
```

### Task 2: Fix progress rendering semantics and in-place terminal refresh

**Files:**
- Modify: `experiments/progress.py`
- Modify: `experiments/run_exp1_split.py`

**Step 1: Implement minimal rendering changes**

- Add a helper that formats the split snapshot with:
  - `point_runs`
  - `algorithms_per_point`
  - `algorithm_runs=x/y`
- Render each point line as:
  - `|Γ|=1000 algo=1/6:capa ...`
- Add a helper to wrap the rendered block with ANSI clear-screen/home escape codes for in-place refresh.

**Step 2: Wire overwrite rendering into the split launcher**

- Replace repeated `print()` calls with terminal writes that overwrite the previous block when stdout is a TTY.
- Keep plain append behavior only for non-TTY contexts.

**Step 3: Run tests**

Run:

```bash
python3 -m unittest tests.test_experiment_progress tests.test_paper_experiments -v
```

Expected: PASS.

**Step 4: Commit**

```bash
git add experiments/progress.py experiments/run_exp1_split.py tests/test_experiment_progress.py tests/test_paper_experiments.py
git commit -m "fix(experiments): overwrite exp1 terminal progress and clarify labels"
```

### Task 3: Emit parcel-level CAPA progress inside one batch

**Files:**
- Modify: `capa/cama.py`
- Modify: `capa/dapa.py`
- Modify: `env/chengdu.py`
- Modify: `algorithms/capa_runner.py`

**Step 1: Add callback hooks**

- Extend `run_cama()` with an optional progress callback.
- Extend `run_dapa()` with an optional progress callback.
- Emit throttled parcel progress events during parcel loops, with fields:
  - `phase`
  - `detail`
  - `completed_units`
  - `total_units`
  - `unit_label`

**Step 2: Bridge these callbacks from the Chengdu batch runner**

- When a batch starts, keep the existing batch event.
- During CAMA and DAPA, forward parcel-level progress into the point progress sink.
- Update detail text to show both batch and parcel position, e.g. `batch 1/2 cama 150/1000`.

**Step 3: Run tests**

Run:

```bash
python3 -m unittest tests.test_chengdu_runner tests.test_capa_local tests.test_capa_auction -v
```

Expected: PASS.

**Step 4: Commit**

```bash
git add capa/cama.py capa/dapa.py env/chengdu.py algorithms/capa_runner.py tests/test_chengdu_runner.py
git commit -m "feat(capa): emit intra-batch exp1 progress events"
```

### Task 4: Run a small split smoke and assess optimization effectiveness

**Files:**
- No required source changes unless bugs remain

**Step 1: Run a small split experiment**

Run:

```bash
python3 -u experiments/run_exp1_split.py \
  --tmp-root /tmp/exp1_progress_debug_small \
  --output-dir outputs/plots/exp1_progress_debug_small \
  --algorithms capa greedy basegta impgta \
  --data-dir Data \
  --local-couriers 20 \
  --platforms 2 \
  --couriers-per-platform 5 \
  --courier-capacity 50 \
  --service-radius-km 1.0 \
  --batch-size 30 \
  --poll-seconds 2
```

**Step 2: Verify**

- Progress updates overwrite in place.
- Top summary labels are no longer misleading.
- CAPA shows intra-batch parcel progress instead of sitting unchanged at `batch 1/n`.
- Small run completes and writes summaries.

**Step 3: Run targeted regression if additional fixes were required**

Run:

```bash
python3 -m unittest discover -s tests -v
```

Expected: PASS.

**Step 4: Commit if any additional code changed during smoke debugging**

```bash
git add <changed files>
git commit -m "fix(experiments): stabilize exp1 progress smoke run"
```
