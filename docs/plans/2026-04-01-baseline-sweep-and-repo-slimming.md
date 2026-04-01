# Baseline Sweep And Repo Slimming Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a reusable Chengdu baseline experiment entrypoint, run larger Chengdu sweeps on the unified environment, and remove dead duplicate code paths that are no longer part of the official implementation.

**Architecture:** Keep `env/` as the only Chengdu environment layer. Add one baseline runner module that consumes `LegacyChengduEnvironment` and returns the same result schema shape used by CAPA experiments. Extend `capa/experiments.py` with baseline and larger sweep helpers. Remove compatibility shims and duplicate legacy copies that are no longer imported by any official runner.

**Tech Stack:** Python, unittest, legacy Chengdu framework modules, CAPA package modules, matplotlib.

---

### Task 1: Write failing tests for unified baseline entrypoints

**Files:**
- Modify: `tests/test_capa_experiment.py`
- Create: `tests/test_baseline_runner.py`

**Step 1: Write the failing test**

Add tests for:
- a `run_chengdu_greedy_baseline()` helper returning a summary-compatible result
- a `run_chengdu_comparison_sweep()` helper that can execute CAPA and Greedy over the same fixed config grid
- result summaries using the same `TR/CR/BPT/delivered/accepted` metric keys

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_capa_experiment tests.test_baseline_runner -v`
Expected: FAIL because no baseline experiment helper exists yet.

**Step 3: Commit**

```bash
git add tests/test_capa_experiment.py tests/test_baseline_runner.py
git commit -m "test(experiments): cover unified Chengdu baseline entrypoints"
```

### Task 2: Implement env-backed Greedy baseline runner

**Files:**
- Create: `baselines/__init__.py`
- Create: `baselines/greedy.py`
- Modify: `capa/experiments.py`

**Step 1: Write minimal implementation**

Create one official baseline runner that:
- builds or accepts `LegacyChengduEnvironment`
- uses the legacy Chengdu `Greedy()` logic as the decision rule
- returns a small immutable baseline result record or summary dict compatible with experiment aggregation
- persists plots and summaries in the same output structure used by CAPA runs

**Step 2: Run targeted tests**

Run: `python3 -m unittest tests.test_capa_experiment tests.test_baseline_runner -v`
Expected: PASS

**Step 3: Commit**

```bash
git add baselines/__init__.py baselines/greedy.py capa/experiments.py
git commit -m "feat(baseline): add unified Chengdu Greedy experiment entrypoint"
```

### Task 3: Add larger Chengdu sweep helpers and run official sweeps

**Files:**
- Modify: `capa/experiments.py`
- Modify: `docs/implementation_notes.md`
- Create: `outputs/plots/chengdu_sweep_large_*`

**Step 1: Write the failing test**

Add tests asserting:
- larger sweep helpers can aggregate multiple runs without changing the summary schema
- comparison sweep output contains both `capa` and `greedy` sections

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_capa_experiment tests.test_baseline_runner -v`
Expected: FAIL because comparison sweep support does not exist yet.

**Step 3: Write minimal implementation**

Implement helpers for:
- one-dimensional larger CAPA sweep
- one-dimensional CAPA vs Greedy comparison sweep

Then run a larger Chengdu sweep with values closer to the paper scale while staying computationally tractable on the local machine.

**Step 4: Run verification**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS

**Step 5: Commit**

```bash
git add capa/experiments.py docs/implementation_notes.md outputs/plots/chengdu_sweep_large_* tests/test_capa_experiment.py tests/test_baseline_runner.py
git commit -m "experiment(chengdu): add larger sweeps and baseline comparison runs"
```

### Task 4: Remove dead duplicate code paths

**Files:**
- Delete: `capa/chengdu_env.py`
- Delete: `MyMethod/Auction_Framework_Chengdu.py`
- Delete: `refactor/algorithm.py`
- Delete: `refactor/data.py`
- Delete: `refactor/entity.py`
- Delete: `refactor/framework.py`
- Delete: `refactor/graph.py`
- Delete: `refactor/method_utils.py`
- Modify: `docs/implementation_notes.md`

**Step 1: Write the failing test**

Add a test asserting official imports and runners do not depend on the deleted files.

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_baseline_runner tests.test_capa_experiment -v`
Expected: FAIL if any runtime path still imports those files.

**Step 3: Write minimal implementation**

Delete the dead files and update documentation to mark `env/`, `capa/`, and `baselines/` as the only maintained runtime paths.

**Step 4: Run full verification**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS

**Step 5: Commit**

```bash
git add -A
git commit -m "refactor(repo): remove dead legacy experiment duplicates"
```
