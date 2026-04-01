# Chengdu Paper Experiment Suite And BPT Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Chengdu-backed paper-style experiment scripts for the implemented algorithms and fix BPT so it only reports assignment-decision time rather than route simulation, routing, or insertion-search overhead.

**Architecture:** Keep `env/chengdu.py` as the single simulation source, build a paper-style experiment layer in `experiments/`, and add a timing-profiler abstraction that separates assignment-decision time from route-feasibility and movement time. Reuse the unified runner/registry so every script shares the same environment construction, seeding, cloning, and output format.

**Tech Stack:** Python 3.12, `unittest`, `concurrent.futures.ProcessPoolExecutor`, existing unified runner/registry, matplotlib.

---

### Task 1: Lock the paper-style Chengdu experiment specification

**Files:**
- Modify: `experiments/suites.py`
- Create: `experiments/paper_config.py`
- Test: `tests/test_experiment_suites.py`

**Step 1: Write the failing test**

Add tests that assert:
- the Chengdu paper-style suite exposes the paper axes `num_parcels`, `local_couriers`, `service_radius`, `platforms`, and `courier_capacity`
- the default algorithm list contains `capa`, `greedy`, `ramcom`, `mra`, `basegta`, `impgta`
- the default preset values mirror Table 2 as closely as the Chengdu environment supports

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_experiment_suites -v`

Expected: FAIL because the new paper-config manifest does not exist yet.

**Step 3: Write minimal implementation**

Create a dedicated paper-config module that:
- declares supported Chengdu paper axes
- stores default axis values and default algorithm order
- distinguishes the unsupported paper-only pieces, e.g. `RL-CAPA` and NYTaxi/Synthetic-specific datasets

Refactor `experiments/suites.py` to consume that config instead of embedding hard-coded values.

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_experiment_suites -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add experiments/paper_config.py experiments/suites.py tests/test_experiment_suites.py
git commit -m "feat(experiments): define Chengdu paper experiment presets"
```

### Task 2: Add a timing profiler contract for assignment-only BPT

**Files:**
- Create: `experiments/timing.py`
- Modify: `capa/models.py`
- Modify: `capa/metrics.py`
- Test: `tests/test_bpt_timing.py`

**Step 1: Write the failing test**

Add tests that assert:
- BPT is computed from `decision_time_seconds`
- routing, insertion, and movement counters do not contribute to the final reported BPT
- batch summaries preserve both the reported BPT and the excluded timing fields

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_bpt_timing -v`

Expected: FAIL because the timing-profiler model does not exist.

**Step 3: Write minimal implementation**

Add a reusable timing dataclass that records:
- `decision_time_seconds`
- `routing_time_seconds`
- `insertion_time_seconds`
- `movement_time_seconds`

Extend batch/run metric models so BPT uses `decision_time_seconds` only, while the excluded timings stay available for audit output.

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_bpt_timing -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add experiments/timing.py capa/models.py capa/metrics.py tests/test_bpt_timing.py
git commit -m "feat(metrics): add assignment-only BPT timing model"
```

### Task 3: Refactor CAPA timing to exclude routing and movement overhead

**Files:**
- Modify: `env/chengdu.py`
- Modify: `capa/cama.py`
- Modify: `capa/dapa.py`
- Modify: `capa/utility.py`
- Test: `tests/test_capa_runner.py`
- Test: `tests/test_bpt_timing.py`

**Step 1: Write the failing test**

Add a regression test that drives one batch with:
- one local decision
- one insertion search
- one movement callback

Assert that:
- reported BPT only increases with assignment-decision time
- insertion search and movement counters are recorded but excluded from the public BPT

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_capa_runner tests.test_bpt_timing -v`

Expected: FAIL because CAPA currently accumulates full wall-clock matching time into BPT.

**Step 3: Write minimal implementation**

Refactor CAPA timing so:
- movement/drain time is tracked separately in `env/chengdu.py`
- insertion search in `capa/utility.py` is timed separately
- the decision logic in `run_cama()` and `run_dapa()` records assignment-only time

Do not change matching behavior; only timing semantics.

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_capa_runner tests.test_bpt_timing -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add env/chengdu.py capa/cama.py capa/dapa.py capa/utility.py tests/test_capa_runner.py tests/test_bpt_timing.py
git commit -m "fix(capa): exclude routing and movement from bpt"
```

### Task 4: Refactor baseline timing to exclude routing and insertion overhead

**Files:**
- Modify: `baselines/common.py`
- Modify: `baselines/greedy.py`
- Modify: `baselines/gta.py`
- Modify: `baselines/mra.py`
- Modify: `baselines/ramcom.py`
- Test: `tests/test_baseline_runner.py`
- Test: `tests/test_mra_ramcom.py`
- Test: `tests/test_bpt_timing.py`

**Step 1: Write the failing test**

Add baseline timing tests that assert:
- reported BPT ignores simulated movement time
- MRA/RamCOM/GTA timing excludes feasible-insertion and route-cost measurement time
- Greedy normalization preserves the legacy BPT field while exposing any unavailable breakdown as zero

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_baseline_runner tests.test_mra_ramcom tests.test_bpt_timing -v`

Expected: FAIL because baseline runners currently report full processing wall time.

**Step 3: Write minimal implementation**

Refactor baseline timing code to:
- time decision logic separately from route-feasibility helpers
- keep output shape stable (`TR`/`CR`/`BPT`)
- optionally store excluded timing counters in the summary JSON for auditability

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_baseline_runner tests.test_mra_ramcom tests.test_bpt_timing -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add baselines/common.py baselines/greedy.py baselines/gta.py baselines/mra.py baselines/ramcom.py tests/test_baseline_runner.py tests/test_mra_ramcom.py tests/test_bpt_timing.py
git commit -m "fix(baselines): report assignment-only bpt"
```

### Task 5: Add a parallel shared-seed experiment harness

**Files:**
- Create: `experiments/parallel.py`
- Modify: `experiments/compare.py`
- Modify: `experiments/seeding.py`
- Test: `tests/test_experiments_seeding.py`
- Test: `tests/test_runner_cli.py`

**Step 1: Write the failing test**

Add tests that assert:
- one sweep point builds one Chengdu environment seed
- parallel algorithm execution receives cloned environments derived from the same seed
- CLI/config can set `max_workers`

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_experiments_seeding tests.test_runner_cli -v`

Expected: FAIL because no parallel harness exists.

**Step 3: Write minimal implementation**

Implement a process-based comparison helper that:
- builds the seed once per sweep point in the parent process
- serializes a seed payload suitable for worker processes
- reconstructs a fresh environment clone per algorithm in workers
- writes each algorithm’s summary into the existing directory layout

Keep a serial fallback path for tests and low-worker runs, but do not add behavior-changing fallback logic.

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_experiments_seeding tests.test_runner_cli -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add experiments/parallel.py experiments/compare.py experiments/seeding.py tests/test_experiments_seeding.py tests/test_runner_cli.py
git commit -m "feat(experiments): parallelize shared-seed algorithm sweeps"
```

### Task 6: Add paper-style Chengdu experiment scripts

**Files:**
- Create: `experiments/run_chengdu_exp1_num_parcels.py`
- Create: `experiments/run_chengdu_exp2_couriers.py`
- Create: `experiments/run_chengdu_exp3_radius.py`
- Create: `experiments/run_chengdu_exp4_platforms.py`
- Create: `experiments/run_chengdu_exp5_default_compare.py`
- Create: `experiments/run_chengdu_paper_suite.py`
- Modify: `experiments/plotting.py`
- Test: `tests/test_experiment_plotting.py`
- Test: `tests/test_runner_cli.py`

**Step 1: Write the failing test**

Add tests that assert:
- each paper script builds the expected sweep axis and algorithm list
- each script writes plot files and a summary manifest
- the default compare script produces paper-style TR/CR/BPT figures for the supported algorithms

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_experiment_plotting tests.test_runner_cli -v`

Expected: FAIL because the dedicated paper scripts do not exist yet.

**Step 3: Write minimal implementation**

Create thin script entrypoints in `experiments/` that:
- consume the paper config defaults
- launch the unified comparison harness
- emit paper-style figure names and a manifest
- keep RL-CAPA out of runnable defaults until it is actually implemented

Add an umbrella script that runs all supported Chengdu paper experiments in sequence.

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_experiment_plotting tests.test_runner_cli -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add experiments/run_chengdu_exp1_num_parcels.py experiments/run_chengdu_exp2_couriers.py experiments/run_chengdu_exp3_radius.py experiments/run_chengdu_exp4_platforms.py experiments/run_chengdu_exp5_default_compare.py experiments/run_chengdu_paper_suite.py experiments/plotting.py tests/test_experiment_plotting.py tests/test_runner_cli.py
git commit -m "feat(experiments): add Chengdu paper experiment scripts"
```

### Task 7: Verify, document, and reconcile CLI/docs

**Files:**
- Modify: `runner.py`
- Modify: `README.md`
- Modify: `docs/implementation_notes.md`
- Test: `tests/test_runner_cli.py`

**Step 1: Write the failing test**

Add CLI/documentation tests that assert:
- the runner exposes the new paper experiment entrypoints or forwarding commands
- README documents the Chengdu paper experiment scripts and the BPT definition

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_runner_cli -v`

Expected: FAIL because the new commands/docs are not documented.

**Step 3: Write minimal implementation**

Update docs and CLI so users can:
- run each paper experiment directly
- run the whole Chengdu paper suite
- understand that reported BPT excludes route planning, insertion search, and movement

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_runner_cli tests.test_experiment_suites tests.test_experiment_plotting tests.test_bpt_timing tests.test_baseline_runner tests.test_mra_ramcom tests.test_capa_runner -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add runner.py README.md docs/implementation_notes.md tests/test_runner_cli.py
git commit -m "docs(experiments): document Chengdu paper suite and bpt semantics"
```
