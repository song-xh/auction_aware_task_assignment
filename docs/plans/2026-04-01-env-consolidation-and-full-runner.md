# Chengdu Env Consolidation And Full Runner Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the Chengdu experiment runner use a reusable environment package, preserve the legacy simulation semantics, and run batches until the experiment reaches a paper-consistent completion boundary instead of stopping at assignment only.

**Architecture:** Extract the legacy Chengdu preprocessing and simulation adapters into an `env/` package that owns dataset loading, station/courier seeding, movement stepping, and assignment write-back. Keep `capa/` as the policy layer only. Update the experiment runner to consume the reusable environment interface, distinguish local versus cooperating platforms explicitly, and continue stepping after matching until all accepted parcels are physically completed. Remove or deprecate duplicate experimental scripts once the new interface is verified.

**Tech Stack:** Python, unittest, legacy Chengdu framework modules, CAPA package modules.

---

### Task 1: Write failing tests for full-run semantics and reusable env boundaries

**Files:**
- Create: `tests/test_env_chengdu.py`
- Modify: `tests/test_chengdu_runner.py`

**Step 1: Write the failing test**

Add tests for:
- environment snapshots distinguishing local and partner courier pools
- assignment write-back preserving insertion order and route state
- runner completion semantics: metrics and result status should depend on delivered parcels, not only matched parcels
- post-batch draining: when the last batch ends but couriers still carry parcels, the environment continues stepping until routes are empty
- reusable environment facade returning movement hook, write-back, and courier grouping in one place

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_env_chengdu tests.test_chengdu_runner -v`
Expected: FAIL because the current code keeps env logic inside `capa/chengdu_env.py` and stops after matching windows.

**Step 3: Commit**

```bash
git add tests/test_env_chengdu.py tests/test_chengdu_runner.py
git commit -m "test(env): cover full-run semantics and reusable env facade"
```

### Task 2: Extract reusable Chengdu env package

**Files:**
- Create: `env/__init__.py`
- Create: `env/chengdu.py`
- Modify: `capa/experiments.py`
- Modify: `capa/__init__.py`

**Step 1: Write minimal implementation**

Move the reusable logic out of `capa/chengdu_env.py` into `env/chengdu.py`:
- station blueprint caching
- task limiting and station assignment helpers
- legacy task/courier/platform snapshot adapters
- assignment write-back helpers
- movement callback and run-to-empty helper
- environment builder returning a stable dict-like interface

Keep docstrings on every function. Re-export the official environment entrypoints from `env/__init__.py`.

**Step 2: Run targeted tests**

Run: `python3 -m unittest tests.test_env_chengdu tests.test_chengdu_runner -v`
Expected: PASS

**Step 3: Commit**

```bash
git add env/__init__.py env/chengdu.py capa/experiments.py capa/__init__.py
git commit -m "refactor(env): extract reusable Chengdu environment package"
```

### Task 3: Fix runner completion semantics and result accounting

**Files:**
- Modify: `env/chengdu.py`
- Modify: `capa/metrics.py`
- Modify: `capa/models.py`
- Modify: `tests/test_env_chengdu.py`
- Modify: `tests/test_chengdu_runner.py`

**Step 1: Write the failing test**

Add tests that assert:
- `completion_rate` reflects delivered parcels rather than accepted assignments
- result objects preserve both accepted assignments and final delivered parcel count
- batch reports keep unresolved-by-assignment separate from in-transit-yet-accepted parcels where needed

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_env_chengdu tests.test_chengdu_runner -v`
Expected: FAIL because the current metric code uses `len(assignments) / total_parcels`.

**Step 3: Write minimal implementation**

Adjust models and metrics so the runner can report:
- accepted assignment plan
- undelivered parcels after assignment
- delivered parcel count after full movement drain
- completion rate based on delivered parcels over requested parcels

Update the env runner to keep stepping until active couriers have empty routes after the final batch.

**Step 4: Run targeted tests**

Run: `python3 -m unittest tests.test_env_chengdu tests.test_chengdu_runner -v`
Expected: PASS

**Step 5: Commit**

```bash
git add env/chengdu.py capa/metrics.py capa/models.py tests/test_env_chengdu.py tests/test_chengdu_runner.py
git commit -m "fix(env): complete Chengdu runs through physical delivery"
```

### Task 4: Remove duplicate runner paths and deprecated experiment script

**Files:**
- Modify: `MyMethod/Auction_Framework_Chengdu.py`
- Modify: `docs/implementation_notes.md`
- Modify: `tests/test_capa_experiment.py`

**Step 1: Write the failing test**

Add a test asserting the official experiment path imports and uses `env.chengdu`, not `MyMethod/Auction_Framework_Chengdu.py`.

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_capa_experiment -v`
Expected: FAIL if any public CAPA entrypoint still depends on the duplicate script.

**Step 3: Write minimal implementation**

Convert `MyMethod/Auction_Framework_Chengdu.py` into a deprecated compatibility wrapper or remove duplicated runnable logic if it is no longer referenced. Preserve only what is still needed as evidence or migration note. Update implementation notes to document the new source of truth.

**Step 4: Run targeted tests**

Run: `python3 -m unittest tests.test_capa_experiment -v`
Expected: PASS

**Step 5: Commit**

```bash
git add MyMethod/Auction_Framework_Chengdu.py docs/implementation_notes.md tests/test_capa_experiment.py
git commit -m "refactor(experiments): remove duplicate Chengdu runner path"
```

### Task 5: Verify end-to-end and run a real small-scale Chengdu experiment

**Files:**
- Modify: `outputs/plots/...` as generated

**Step 1: Run the full test suite**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS

**Step 2: Run a real Chengdu experiment**

Run: `python3 -m capa.experiments --data-dir Data --num-parcels 5 --local-couriers 2 --platforms 1 --couriers-per-platform 1 --batch-size 60 --output-dir outputs/plots/chengdu_small_real`
Expected: summary and plots generated using the env-backed full-runner path.

**Step 3: Inspect git status**

Run: `git status --short`
Expected: only intended source, test, docs, and output changes remain.

**Step 4: Commit**

```bash
git add -A
git commit -m "feat(env): consolidate reusable Chengdu environment and full experiment runner"
```
