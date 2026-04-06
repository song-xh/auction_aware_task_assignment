# Paper Experiment Entrypoint And Progress Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove the user-facing `run_exp1_*` entrypoint sprawl, route Chengdu paper experiments through the formal `run_chengdu_exp*.py` scripts, and replace duplicate terminal printing with one live progress display that overwrites prior output.

**Architecture:** Keep the generic framework introduced in `experiments/framework/` as the internal execution engine, but move all user-facing orchestration into `experiments/paper_chengdu.py` plus the formal `run_chengdu_exp*.py` scripts. Exp-1 split/managed/point modes become generic paper-experiment capabilities instead of dedicated top-level scripts. Progress rendering moves to a Rich-based live renderer shared by all long-running Chengdu paper experiments.

**Tech Stack:** Python, Rich, existing `experiments/framework/*`, Chengdu paper scripts, existing algorithm registry.

---

### Task 1: Add local failing verification for the new paper-entrypoint behavior

**Files:**
- Create: `/tmp/test_paper_entrypoints.py`
- Read: `experiments/paper_chengdu.py`
- Read: `experiments/run_chengdu_exp1_num_parcels.py`

**Step 1: Write a failing verification script**
- Expect `run_chengdu_exp1_num_parcels.py` to support split-managed execution through formal script options.
- Expect the old `run_exp1_*` wrappers to become unnecessary once formal entrypoints absorb that logic.

**Step 2: Run the verification and confirm current behavior is missing**
Run a small invocation against the current script and confirm there is no formal `--execution-mode` / managed-round support.

**Step 3: Implement the paper-entrypoint unification**
- Modify `experiments/paper_chengdu.py`
- Modify `experiments/run_chengdu_exp1_num_parcels.py`
- Modify other `run_chengdu_exp*.py` scripts only as thin wrappers over the shared paper runner
- Remove `experiments/run_exp1_point.py`
- Remove `experiments/run_exp1_split.py`
- Remove `experiments/run_exp1_managed.py`

**Step 4: Re-run the verification**
Run the same small invocation and confirm the new formal script accepts the unified execution options.

**Step 5: Commit**
`git add ... && git commit -m "refactor(experiments): fold exp1 entrypoints into formal paper scripts"`

### Task 2: Replace duplicate terminal printing with one live Rich renderer

**Files:**
- Modify: `experiments/progress.py`
- Modify: `experiments/framework/split_runner.py`
- Modify: `experiments/paper_chengdu.py`

**Step 1: Write a local failing verification script**
- Create `/tmp/test_rich_progress.py`
- Assert the renderer returns/uses a single live display API rather than repeated appended snapshots.

**Step 2: Run it to confirm current behavior is still snapshot-print based**

**Step 3: Implement the live renderer**
- Add a Rich table/panel based summary in `experiments/progress.py`
- Make split execution own one `Live` session and refresh in place
- Preserve the same information: state, completed points, current algorithm, phase, detail, overall progress bar

**Step 4: Re-run the verification**
- Run a tiny split paper experiment and verify the terminal output is single-block live progress instead of repeated snapshots.

**Step 5: Commit**
`git add ... && git commit -m "feat(progress): render Chengdu paper experiments with live progress"`

### Task 3: Synchronize all Chengdu paper experiment scripts onto the same flow and log contract

**Files:**
- Modify: `experiments/paper_chengdu.py`
- Modify: `experiments/run_chengdu_exp2_couriers.py`
- Modify: `experiments/run_chengdu_exp3_radius.py`
- Modify: `experiments/run_chengdu_exp4_platforms.py`
- Modify: `experiments/run_chengdu_exp5_default_compare.py`
- Modify: `experiments/run_chengdu_exp6_capacity.py`
- Modify: `experiments/run_chengdu_paper_suite.py`

**Step 1: Verify the current scripts still use mixed execution paths**
- `Exp-1` has dedicated split/managed wrappers
- others call `run_chengdu_paper_experiment()` directly

**Step 2: Move shared orchestration into `paper_chengdu.py`**
- Introduce generic paper experiment execution modes
- Ensure all scripts expose the same CLI contract where applicable
- Ensure all scripts emit the same progress semantics and log shape

**Step 3: Run tiny smoke experiments for at least Exp-1 and one non-Exp-1 axis**
- `num_parcels`
- `local_couriers` or `platforms`

**Step 4: Commit**
`git add ... && git commit -m "refactor(experiments): unify Chengdu paper script orchestration"`

### Task 4: Full verification

**Files:**
- No new files required

**Step 1: Run compile checks**
`python3 -m py_compile ...`

**Step 2: Run tiny smoke experiments**
- Formal Exp-1 via `run_chengdu_exp1_num_parcels.py`
- At least one other formal script

**Step 3: Inspect worktree and finalize**
- `git status --short`
- confirm no stray wrapper references remain

**Step 4: Final commit if needed**
`git add -A && git commit -m "fix(experiments): finalize unified paper experiment entrypoints"`
