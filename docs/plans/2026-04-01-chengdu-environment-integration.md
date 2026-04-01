# Chengdu Environment Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rework the Chengdu experiment path so it reuses the repository's original time-stepped simulation environment and only swaps in the repaired CAPA assignment logic.

**Architecture:** Keep the original Chengdu environment as the source of truth for station generation, initial courier schedules, route insertion side effects, and movement progression. Add a thin adapter layer that reads legacy courier/task/platform state into CAPA decision inputs, then writes accepted assignments back into legacy objects without changing the simulation semantics. Keep the synthetic `build_entities_from_locations` path out of the official Chengdu runner.

**Tech Stack:** Python 3, `unittest`, existing Chengdu graph/task loaders, legacy simulation modules, `capa/` assignment modules.

---

### Task 1: Lock the official experiment boundary with failing tests

**Files:**
- Create: `tests/test_chengdu_runner.py`
- Modify: `tests/test_capa_experiment.py`

**Step 1: Write the failing test**

Add tests that assert:
- the official Chengdu experiment builder uses legacy environment hooks instead of `build_entities_from_locations`
- the Chengdu runner advances couriers through an injected movement callback each step
- the result summary still exposes `TR`, `CR`, and `BPT`

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_chengdu_runner -v`
Expected: FAIL because no environment-preserving runner exists yet

**Step 3: Write minimal implementation**

Create a new Chengdu runner entrypoint wired to injected legacy environment callbacks.

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_chengdu_runner -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_chengdu_runner.py tests/test_capa_experiment.py capa
git commit -m "test(capa): add Chengdu environment runner coverage"
```

### Task 2: Introduce legacy environment adapters

**Files:**
- Create: `capa/chengdu_env.py`
- Modify: `capa/__init__.py`
- Test: `tests/test_chengdu_runner.py`

**Step 1: Write the failing test**

Add tests for:
- converting legacy couriers/tasks into CAPA decision candidates
- applying a chosen local assignment back into `re_schedule`, `re_weight`, and timing state
- applying a chosen cross assignment to a partner courier with the same write-back semantics

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_chengdu_runner -v`
Expected: FAIL because adapter functions do not exist

**Step 3: Write minimal implementation**

Implement adapter helpers with docstrings:
- legacy courier/task inspection
- legacy-to-CAPA temporary model conversion
- assignment write-back into legacy objects
- metric bookkeeping helpers

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_chengdu_runner -v`
Expected: PASS

**Step 5: Commit**

```bash
git add capa/chengdu_env.py capa/__init__.py tests/test_chengdu_runner.py
git commit -m "feat(capa): add legacy Chengdu environment adapters"
```

### Task 3: Replace the official Chengdu experiment runner

**Files:**
- Modify: `capa/experiments.py`
- Modify: `capa/__init__.py`
- Test: `tests/test_capa_experiment.py`
- Test: `tests/test_chengdu_runner.py`

**Step 1: Write the failing test**

Extend tests to assert:
- `run_chengdu_experiment` delegates to the legacy-environment-backed runner
- `build_entities_from_locations` is no longer required by the official path
- summary and plots remain materialized

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_capa_experiment tests.test_chengdu_runner -v`
Expected: FAIL because `run_chengdu_experiment` still uses the synthetic builder

**Step 3: Write minimal implementation**

Refactor `capa/experiments.py` so the official Chengdu path:
- loads legacy tasks
- builds stations and couriers from the original environment
- runs a time-stepped batch loop with legacy movement
- uses CAPA decision functions through the adapter layer

Keep synthetic helpers, if retained, clearly separated from the official runner.

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_capa_experiment tests.test_chengdu_runner -v`
Expected: PASS

**Step 5: Commit**

```bash
git add capa/experiments.py capa/__init__.py tests/test_capa_experiment.py tests/test_chengdu_runner.py
git commit -m "feat(capa): route Chengdu experiments through legacy simulation"
```

### Task 4: Update documentation to reflect the corrected experiment path

**Files:**
- Modify: `docs/implementation_notes.md`

**Step 1: Write the failing test**

No automated doc test. Use the previously added behavior tests as the safety net.

**Step 2: Run test to verify the code stays green**

Run: `python3 -m unittest tests.test_capa_experiment tests.test_chengdu_runner -v`
Expected: PASS

**Step 3: Write minimal implementation**

Update the notes to state that the official Chengdu runner now reuses the legacy environment and explicitly document any remaining ambiguity around partner-platform construction.

**Step 4: Run broader verification**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS

**Step 5: Commit**

```bash
git add docs/implementation_notes.md capa tests
git commit -m "docs(capa): document legacy-backed Chengdu experiment path"
```
