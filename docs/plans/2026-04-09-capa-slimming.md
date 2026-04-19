# CAPA Utility Slimming Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Slim the `capa/` package by merging tool-only modules into `capa/utility.py`, updating imports, deleting the old tool files, and preserving CAPA behavior.

**Architecture:** Keep `cama.py`, `dapa.py`, `runner.py`, `models.py`, `metrics.py`, `config.py`, and `constraints.py` as the readable CAPA core. Move helper-only code from `cache.py`, `geo.py`, `timing.py`, `batch_distance.py`, `travel.py`, and `revenue.py` into `utility.py`, then repoint imports across CAPA, baselines, env, experiments, and RL wrappers.

**Tech Stack:** Python, `unittest`, existing CAPA / Chengdu regression tests.

---

### Task 1: Write the refactor guard test

**Files:**
- Create: `tests/test_capa_utility_slimming.py`
- Test: `tests/test_capa_utility_slimming.py`

**Step 1: Write the failing test**

Add tests that assert:
- `capa.utility` exports `InsertionCache`, `GeoIndex`, `TimingAccumulator`, `TimedTravelModel`, `BatchDistanceMatrix`, and `PersistentDirectedDistanceCache`
- the old utility-only files no longer exist:
  - `capa/cache.py`
  - `capa/geo.py`
  - `capa/timing.py`
  - `capa/batch_distance.py`
  - `capa/travel.py`
  - `capa/revenue.py`

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_capa_utility_slimming -v`

Expected: FAIL because the old files still exist and `utility.py` does not yet expose the full merged API.

### Task 2: Merge cache / geo / timing helpers into `utility.py`

**Files:**
- Modify: `capa/utility.py`
- Modify: `capa/models.py`
- Test: `tests/test_capa_utility_slimming.py`

**Step 1: Write minimal implementation**

Move into `utility.py`:
- `RouteSignature`
- `InsertionResult`
- `build_courier_route_signature`
- `InsertionCache`
- `EARTH_RADIUS_KM`
- `haversine_km`
- `haversine_meters`
- `GeoIndex`
- `TimingAccumulator`
- `TimedTravelModel`

Keep `BatchTimingBreakdown` in `models.py` to avoid the `models.py <-> utility.py` import cycle.

Add Chinese section comments for the merged tool groups.

**Step 2: Run focused test**

Run: `python -m unittest tests.test_capa_utility_slimming -v`

Expected: still FAIL because distance-cache wrappers and old files remain.

### Task 3: Merge distance-cache and compatibility wrappers

**Files:**
- Modify: `capa/utility.py`
- Modify: `env/chengdu.py`
- Modify: `baselines/common.py`
- Modify: `baselines/greedy.py`
- Modify: `baselines/mra.py`
- Modify: `baselines/ramcom.py`
- Modify: `baselines/gta.py`
- Modify: `capa/cama.py`
- Modify: `capa/dapa.py`
- Modify: `capa/runner.py`
- Modify: `capa/__init__.py`
- Modify: `algorithms/*_runner.py` as needed
- Modify: `rl_capa/*` as needed
- Modify: `experiments/*` as needed
- Test: `tests/test_capa_utility_slimming.py`

**Step 1: Write minimal implementation**

Move into `utility.py`:
- `PersistentDirectedDistanceCache`
- `BatchDistanceMatrix`
- the `travel.py` compatibility export target (`DistanceMatrixTravelModel` is already here)
- the `revenue.py` compatibility export target (already here)

Then update every import site so no code imports from the soon-to-be-deleted files.

**Step 2: Run focused test**

Run: `python -m unittest tests.test_capa_utility_slimming -v`

Expected: still FAIL until the old files are actually deleted.

### Task 4: Delete the old tool modules

**Files:**
- Delete: `capa/cache.py`
- Delete: `capa/geo.py`
- Delete: `capa/timing.py`
- Delete: `capa/batch_distance.py`
- Delete: `capa/travel.py`
- Delete: `capa/revenue.py`
- Test: `tests/test_capa_utility_slimming.py`

**Step 1: Delete the files**

Remove the superseded modules once all imports point to `utility.py`.

**Step 2: Run focused test**

Run: `python -m unittest tests.test_capa_utility_slimming -v`

Expected: PASS.

### Task 5: Run CAPA regression suite

**Files:**
- Modify: none
- Test: existing tests

**Step 1: Run regression commands**

Run:

```bash
python -m unittest tests.test_capa_utility_slimming tests.test_capa_config tests.test_capa_local tests.test_capa_auction tests.test_capa_warmup tests.test_mra_bpt tests.test_graph_utils_chengdu -v
```

Expected: PASS.

### Task 6: Inspect and commit

**Files:**
- Modify: none

**Step 1: Inspect worktree**

Run: `git status --short`

Expected: only the intended slimming changes, plus the pre-existing edit in `capa/config.py`.

**Step 2: Commit**

```bash
git add -A
git commit -m "refactor(capa): merge utility-only modules"
```
