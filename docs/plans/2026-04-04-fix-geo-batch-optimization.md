# Geo And Batch Optimization Fix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Repair the geometric pre-filter and batch-distance optimization so they preserve Chengdu routing correctness, are actually used by the unified runner, and measurably reduce routing work before becoming part of the formal experiment baseline.

**Architecture:** Keep the optimization inside the shared Chengdu environment and shared CAPA/baseline helpers rather than the ad-hoc `capa.experiments` path. Replace the incorrect all-pairs symmetric cache with a directed, insertion-specific batch distance cache, and thread one shared `GeoIndex` plus travel speed through the environment and algorithm runners.

**Tech Stack:** Python, unittest, legacy Chengdu graph adapters, unified runner, CAPA/baseline modules.

---

### Task 1: Add failing tests for the current regression points

**Files:**
- Modify: `tests/test_geo_and_batch_distance.py`
- Modify: `tests/test_runner_cli.py`
- Modify: `tests/test_baseline_runner.py`

**Step 1: Write the failing tests**

- Add a directed-distance test proving `BatchDistanceMatrix` must not mirror `a -> b` into `b -> a`.
- Add a runner-path test proving the unified CAPA runner forwards optimization context from the environment into `run_time_stepped_chengdu_batches()`.
- Add a baseline-path test proving geometric pre-filter context can flow through the unified baseline path rather than only `capa.experiments`.
- Add a selective-precompute test proving the batch matrix warms only insertion-related pairs instead of full all-pairs over active nodes.

**Step 2: Run the focused tests to verify they fail**

Run:
```bash
python3 -m unittest tests.test_geo_and_batch_distance tests.test_runner_cli tests.test_baseline_runner -v
```

Expected:
- at least one failure showing the current optimization path is incorrect or not wired into the unified runner.

**Step 3: Commit the red test stage**

```bash
git add tests/test_geo_and_batch_distance.py tests/test_runner_cli.py tests/test_baseline_runner.py
git commit -m "test: cover directed batch cache and runner optimization wiring"
```

### Task 2: Repair the optimization architecture in the shared environment

**Files:**
- Modify: `env/chengdu.py`
- Modify: `capa/batch_distance.py`
- Modify: `capa/geo.py`
- Modify: `capa/cama.py`
- Modify: `capa/dapa.py`
- Modify: `capa/constraints.py`

**Step 1: Implement the minimal fix**

- Extend `ChengduEnvironment` to carry reusable optimization context such as `geo_index` and `travel_speed_m_per_s`.
- Build that context once in `build_framework_chengdu_environment()`.
- Replace the symmetric all-pairs cache with a directed batch cache.
- Replace full-node all-pairs precompute with insertion-specific pair warmup:
  - consecutive route edges
  - route-node to parcel
  - parcel to route-node
- Keep fallback exact lookup for uncached pairs.

**Step 2: Run the focused tests again**

Run:
```bash
python3 -m unittest tests.test_geo_and_batch_distance tests.test_runner_cli tests.test_baseline_runner -v
```

Expected:
- the new tests pass

**Step 3: Commit the environment/cache repair**

```bash
git add env/chengdu.py capa/batch_distance.py capa/geo.py capa/cama.py capa/dapa.py capa/constraints.py
git commit -m "fix(env): repair directed geo and batch cache integration"
```

### Task 3: Wire the optimization through the formal runner and baselines

**Files:**
- Modify: `algorithms/capa_runner.py`
- Modify: `algorithms/greedy_runner.py`
- Modify: `algorithms/mra_runner.py`
- Modify: `algorithms/ramcom_runner.py`
- Modify: `baselines/common.py`
- Modify: `baselines/greedy.py`
- Modify: `baselines/mra.py`
- Modify: `baselines/ramcom.py`

**Step 1: Implement the wiring**

- Make the unified CAPA runner pass environment optimization context into `run_time_stepped_chengdu_batches()`.
- Make the baseline environment helpers read `environment.geo_index` and `environment.travel_speed_m_per_s`.
- Ensure the new optional parameters are used by the actual formal runner path, not only experiment-side helpers.

**Step 2: Run the affected tests**

Run:
```bash
python3 -m unittest tests.test_runner_cli tests.test_baseline_runner tests.test_chengdu_runner -v
```

Expected:
- all affected runner/baseline tests pass

**Step 3: Commit the runner wiring**

```bash
git add algorithms/capa_runner.py algorithms/greedy_runner.py algorithms/mra_runner.py algorithms/ramcom_runner.py baselines/common.py baselines/greedy.py baselines/mra.py baselines/ramcom.py
git commit -m "feat(runner): enable geo and batch optimization in formal runners"
```

### Task 4: Verify the optimization is materially useful

**Files:**
- Modify: `tests/test_geo_and_batch_distance.py`
- Modify: `docs/implementation_notes.md`

**Step 1: Add an evidence-oriented test or benchmark**

- Add one deterministic call-count test showing the directed insertion-specific batch cache reduces underlying distance calls relative to uncached insertion evaluation.
- Record the optimization boundary in `docs/implementation_notes.md`.

**Step 2: Run the verification suite**

Run:
```bash
python3 -m unittest discover -s tests -v
```

Expected:
- full suite green

**Step 3: Capture a small benchmark**

Run a small local benchmark or call-count script and record:
- uncached routing calls
- cached routing calls
- reduction percentage

**Step 4: Commit the verification/docs**

```bash
git add tests/test_geo_and_batch_distance.py docs/implementation_notes.md
git commit -m "test: verify optimization benefit and document cache boundaries"
```

### Task 5: Merge the repaired branch back to main

**Files:**
- No code changes required

**Step 1: Confirm the branch is clean and verified**

Run:
```bash
git status --short
git log --oneline -5
```

**Step 2: Merge back to `master`**

Run:
```bash
git checkout master
git merge --ff-only feat/fix-geo-batch-optimization
```

**Step 3: Final verification on `master`**

Run:
```bash
python3 -m unittest discover -s tests -v
```

