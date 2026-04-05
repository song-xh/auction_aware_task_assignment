# Exp1 Progress Overwrite Fix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make `experiments/run_exp1_split.py` show only the latest progress block by default in user terminals, while preserving an explicit append mode when needed.

**Architecture:** Treat the issue as a progress-mode selection bug. Move overwrite/append choice into an explicit helper with a CLI flag, default the experiment runner to overwrite-oriented behavior, and keep formatting logic in `experiments/progress.py`.

**Tech Stack:** Python, unittest, existing Chengdu experiment runners.

---

### Task 1: Add failing tests for progress mode resolution and CLI forwarding

**Files:**
- Modify: `tests/test_experiment_progress.py`
- Modify: `tests/test_paper_experiments.py`

**Step 1: Write the failing tests**

- Add a test that progress mode defaults to `overwrite`.
- Add a test that `render_terminal_progress_block(..., overwrite=True)` still wraps blocks for overwrite mode.
- Add a CLI-forwarding test for `--progress-mode append`.

**Step 2: Run tests to verify they fail**

Run:

```bash
python3 -m unittest tests.test_experiment_progress tests.test_paper_experiments -v
```

Expected: FAIL because no explicit progress-mode resolver exists and the CLI does not expose `--progress-mode`.

**Step 3: Commit**

```bash
git add tests/test_experiment_progress.py tests/test_paper_experiments.py
git commit -m "test(experiments): cover exp1 progress mode selection"
```

### Task 2: Implement explicit progress mode selection

**Files:**
- Modify: `experiments/progress.py`
- Modify: `experiments/run_exp1_split.py`

**Step 1: Add a resolver helper**

- Add a `resolve_progress_mode(mode, stream)` helper.
- Support `overwrite`, `append`, and `auto`.
- Make the default user-facing behavior resolve to overwrite for terminal-style runs.

**Step 2: Wire the split runner**

- Add `progress_mode` to `run_exp1_split()`.
- Add `--progress-mode` to the CLI parser.
- Route the resolved mode into `render_terminal_progress_block()`.

**Step 3: Run tests**

Run:

```bash
python3 -m unittest tests.test_experiment_progress tests.test_paper_experiments -v
```

Expected: PASS.

**Step 4: Commit**

```bash
git add experiments/progress.py experiments/run_exp1_split.py tests/test_experiment_progress.py tests/test_paper_experiments.py
git commit -m "fix(experiments): default exp1 progress to overwrite mode"
```

### Task 3: Run regression and a tiny smoke

**Files:**
- No required code changes unless tests expose regressions

**Step 1: Run full regression**

Run:

```bash
python3 -m unittest discover -s tests -v
```

Expected: PASS.

**Step 2: Run tiny smoke**

Run:

```bash
python3 experiments/run_exp1_split.py \
  --tmp-root /tmp/exp1_progress_mode_smoke \
  --output-dir outputs/plots/exp1_progress_mode_smoke \
  --algorithms capa greedy \
  --data-dir Data \
  --local-couriers 8 \
  --platforms 1 \
  --couriers-per-platform 2 \
  --courier-capacity 50 \
  --service-radius-km 1.0 \
  --batch-size 30 \
  --poll-seconds 1
```

Verify:
- terminal output uses overwrite mode by default
- summary file is produced

**Step 3: Commit only if smoke required further code changes**

```bash
git add <changed files>
git commit -m "fix(experiments): stabilize exp1 overwrite progress smoke"
```
