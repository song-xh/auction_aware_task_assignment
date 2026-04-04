# CAPA Batch Semantics and Cache Refactor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the Chengdu CAPA runner execute one matching round per batch boundary, and add layered shortest-path, insertion, and courier-snapshot caches to reduce repeated computation across CAPA and the baseline runners.

**Architecture:** Refactor `env/chengdu.py` so the legacy environment advances between batches and matching occurs exactly once at the batch deadline, not incrementally inside the batch. Add reusable cache primitives for legacy-to-CAPA courier projection and best insertion lookup, then wire those caches through CAPA, baseline helpers, and the Chengdu graph travel model.

**Tech Stack:** Python, unittest, legacy Chengdu simulator, CAPA modules, unified Chengdu environment.

---

### Task 1: Lock the batch-boundary semantics in tests

**Files:**
- Modify: `tests/test_chengdu_runner.py`
- Modify: `tests/test_capa_experiment.py`

**Step 1: Write the failing tests**

Add tests that verify:
- tasks arriving at `t=0` and `t=20` with `batch_size=30` appear in the same first batch report
- the first batch report is emitted at the batch boundary rather than at the first parcel time
- `step_seconds > batch_size` no longer causes in-batch parcels to spill into the next batch

**Step 2: Run the targeted tests to verify they fail**

Run:

```bash
python3 -m unittest tests.test_chengdu_runner tests.test_capa_experiment -v
```

Expected: at least one new failure showing the current incremental in-batch matching behavior.

**Step 3: Commit the red test state**

```bash
git add tests/test_chengdu_runner.py tests/test_capa_experiment.py
git commit -m "test(chengdu): capture batch-boundary assignment semantics"
```

### Task 2: Lock the cache behavior in tests

**Files:**
- Create: `tests/test_capa_cache.py`
- Modify: `tests/test_capa_experiment.py`

**Step 1: Write the failing tests**

Add tests that verify:
- repeated `find_best_local_insertion()` calls can reuse a shared insertion cache
- repeated legacy courier projection reuses a shared snapshot cache until the legacy state changes
- `ChengduGraphTravelModel.distance()` prefers a distance-only graph API when available

**Step 2: Run the targeted tests to verify they fail**

Run:

```bash
python3 -m unittest tests.test_capa_cache tests.test_capa_experiment -v
```

Expected: failures because the cache classes and distance-only path have not been implemented yet.

**Step 3: Commit the red test state**

```bash
git add tests/test_capa_cache.py tests/test_capa_experiment.py
git commit -m "test(cache): capture insertion snapshot and graph-distance cache behavior"
```

### Task 3: Refactor Chengdu CAPA runner to match once per batch

**Files:**
- Modify: `env/chengdu.py`
- Modify: `algorithms/capa_runner.py`
- Modify: `docs/implementation_notes.md`

**Step 1: Implement the batch-boundary runner**

Change `run_time_stepped_chengdu_batches()` so it:
- advances the legacy environment to each batch deadline
- performs exactly one `CAMA -> DAPA` round per batch
- carries unresolved parcels to the next batch
- drains accepted routes only after the final batch

**Step 2: Run the targeted tests to verify they pass**

Run:

```bash
python3 -m unittest tests.test_chengdu_runner tests.test_capa_experiment -v
```

Expected: PASS.

**Step 3: Commit**

```bash
git add env/chengdu.py algorithms/capa_runner.py docs/implementation_notes.md tests/test_chengdu_runner.py tests/test_capa_experiment.py
git commit -m "fix(capa): execute Chengdu matching once per batch boundary"
```

### Task 4: Add reusable insertion and courier snapshot caches

**Files:**
- Create: `capa/cache.py`
- Modify: `capa/utility.py`
- Modify: `env/chengdu.py`
- Modify: `baselines/common.py`
- Modify: `tests/test_capa_cache.py`

**Step 1: Implement the cache layer**

Add:
- a route-signature-based insertion cache
- a legacy courier snapshot cache keyed by legacy state

Wire them into:
- `find_best_local_insertion()`
- `calculate_utility()`
- legacy courier projection helpers
- baseline feasible-insertion helper paths

**Step 2: Run the targeted tests to verify they pass**

Run:

```bash
python3 -m unittest tests.test_capa_cache tests.test_capa_local tests.test_capa_auction tests.test_baseline_runner -v
```

Expected: PASS.

**Step 3: Commit**

```bash
git add capa/cache.py capa/utility.py env/chengdu.py baselines/common.py tests/test_capa_cache.py
git commit -m "feat(cache): add shared insertion and courier snapshot caches"
```

### Task 5: Add a distance-only Chengdu shortest-path fast path

**Files:**
- Modify: `GraphUtils_ChengDu.py`
- Modify: `capa/experiments.py`
- Modify: `tests/test_capa_experiment.py`

**Step 1: Implement the fast path**

Add a distance-only shortest-path API in `GraphUtils_ChengDu.py` and make `ChengduGraphTravelModel.distance()` use it when available instead of reconstructing full edge lists.

**Step 2: Run the targeted tests to verify they pass**

Run:

```bash
python3 -m unittest tests.test_capa_experiment tests.test_capa_cache -v
```

Expected: PASS.

**Step 3: Commit**

```bash
git add GraphUtils_ChengDu.py capa/experiments.py tests/test_capa_experiment.py
git commit -m "perf(graph): add distance-only Chengdu shortest-path fast path"
```

### Task 6: Wire caches through CAPA and baseline runners and verify end-to-end

**Files:**
- Modify: `capa/cama.py`
- Modify: `capa/dapa.py`
- Modify: `baselines/greedy.py`
- Modify: `baselines/mra.py`
- Modify: `baselines/ramcom.py`
- Modify: `docs/implementation_notes.md`

**Step 1: Reuse the caches in the hot paths**

Ensure the shared insertion cache and snapshot cache are passed through:
- `CAMA`
- `DAPA`
- `Greedy`
- `MRA`
- `RamCOM`

**Step 2: Run focused plus broad verification**

Run:

```bash
python3 -m unittest tests.test_capa_cache tests.test_chengdu_runner tests.test_capa_local tests.test_capa_auction tests.test_capa_runner tests.test_baseline_runner tests.test_capa_experiment -v
python3 -m unittest discover -s tests -v
```

Expected: PASS.

**Step 3: Commit**

```bash
git add capa/cama.py capa/dapa.py baselines/greedy.py baselines/mra.py baselines/ramcom.py docs/implementation_notes.md
git commit -m "perf(runners): reuse layered caches across CAPA and baselines"
```
