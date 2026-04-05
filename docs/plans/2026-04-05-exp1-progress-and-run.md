# Exp1 Progress And Run Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add live terminal progress reporting for the formal `exp_1` workflow, then launch the full parcel-count experiment with the improved runner output.

**Architecture:** Reuse the existing split-process `exp_1` pipeline instead of inventing a second runner. Each point process will emit a structured `progress.json`, the top-level split launcher will aggregate those snapshots into one terminal progress bar, and CAPA will additionally expose batch-level progress events from the Chengdu batch runner.

**Tech Stack:** Python, unittest, subprocess-based experiment runners, unified Chengdu environment, CAPA runner.

---

### Task 1: Add failing tests for progress reporting

**Files:**
- Modify: `tests/test_paper_experiments.py`
- Modify: `tests/test_chengdu_runner.py`
- Create or modify: `tests/test_experiment_progress.py`

**Step 1: Write the failing tests**

- Add a test proving `run_exp1_point()` writes a `progress.json` file while algorithms execute.
- Add a test proving `collect_split_progress()` reads per-point progress details and exposes them in the aggregate snapshot.
- Add a test proving `run_time_stepped_chengdu_batches()` can emit batch-level progress events for CAPA.
- Add a test proving the progress renderer produces one bar plus human-readable status lines.

**Step 2: Run the focused tests to verify they fail**

Run:
```bash
python3 -m unittest tests.test_paper_experiments tests.test_chengdu_runner tests.test_experiment_progress -v
```

Expected:
- failures showing the current exp1 pipeline lacks structured live progress data.

**Step 3: Commit the red test stage**

```bash
git add tests/test_paper_experiments.py tests/test_chengdu_runner.py tests/test_experiment_progress.py
git commit -m "test: cover exp1 progress reporting"
```

### Task 2: Implement reusable progress reporting primitives

**Files:**
- Create: `experiments/progress.py`
- Modify: `experiments/monitor_exp1_split.py`

**Step 1: Write the minimal implementation**

- Add helpers to:
  - write one structured progress payload to disk
  - render one textual progress bar
  - format split-run snapshots for terminal output
- Extend `collect_split_progress()` to read point-level `progress.json` files when present.

**Step 2: Run the focused tests**

Run:
```bash
python3 -m unittest tests.test_experiment_progress tests.test_paper_experiments -v
```

Expected:
- renderer and snapshot tests pass

**Step 3: Commit**

```bash
git add experiments/progress.py experiments/monitor_exp1_split.py tests/test_experiment_progress.py tests/test_paper_experiments.py
git commit -m "feat(experiments): add reusable exp1 progress reporting"
```

### Task 3: Wire progress through the point and split runners

**Files:**
- Modify: `experiments/run_exp1_point.py`
- Modify: `experiments/run_exp1_split.py`
- Modify: `algorithms/capa_runner.py`
- Modify: `baselines/greedy.py`
- Modify: `baselines/gta.py`
- Modify: `baselines/mra.py`
- Modify: `baselines/ramcom.py`
- Modify: `env/chengdu.py`

**Step 1: Write the minimal implementation**

- Let `run_exp1_point()` create and update `progress.json`:
  - current point
  - algorithm index / total
  - current algorithm
  - detail string
  - per-algorithm fractional progress
- Let `run_exp1_split()` aggregate those point snapshots and print one live terminal progress block each poll.
- Add optional `progress_callback` plumbing so CAPA can report:
  - current batch
  - total batches
  - current phase
- Add lightweight progress events to the baselines using task or batch counts.

**Step 2: Run the focused tests**

Run:
```bash
python3 -m unittest tests.test_paper_experiments tests.test_chengdu_runner tests.test_baseline_runner tests.test_runner_cli -v
```

Expected:
- progress tests and existing runner tests all pass

**Step 3: Commit**

```bash
git add experiments/run_exp1_point.py experiments/run_exp1_split.py algorithms/capa_runner.py baselines/greedy.py baselines/gta.py baselines/mra.py baselines/ramcom.py env/chengdu.py tests/test_paper_experiments.py tests/test_chengdu_runner.py tests/test_baseline_runner.py tests/test_runner_cli.py
git commit -m "feat(exp1): add live terminal progress for split experiments"
```

### Task 4: Verify full regression and launch the formal exp1 run

**Files:**
- No new source files required

**Step 1: Run the full test suite**

Run:
```bash
python3 -m unittest discover -s tests -v
```

Expected:
- full suite green

**Step 2: Start the formal exp1 run**

Run:
```bash
python3 experiments/run_exp1_split.py \
  --tmp-root /tmp/exp1_formal_20260405 \
  --output-dir outputs/plots/exp1_formal_20260405 \
  --algorithms capa greedy basegta impgta mra ramcom \
  --batch-size 30 \
  --local-couriers 200 \
  --platforms 4 \
  --couriers-per-platform 50 \
  --courier-capacity 50 \
  --service-radius-km 1.0 \
  --poll-seconds 10
```

**Step 3: Monitor completion**

- Keep the process running unless it fails.
- Preserve `/tmp` point logs and progress snapshots.
- When the run finishes, inspect `outputs/plots/exp1_formal_20260405/summary.json`.

**Step 4: Commit the implementation branch**

```bash
git status --short
git add -A
git commit -m "experiment(exp1): add progress output and launch formal run"
```

