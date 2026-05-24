# Exp7 Fixed Delay Compare Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Materialize one canonical Chengdu Exp-7 dataset, export fixed local/partner task CSVs under `Data/delay`, generate five delayed local-parcel CSV variants (`5/10/20/30/60s`), and run `capa`, `impgta`, and `ramcom` for baseline plus five delay settings with summaries that emphasize the affected parcels.

**Architecture:** Keep the existing Chengdu environment builder as the source of truth for object construction, then separate the workflow into two layers. Layer 1 builds one canonical environment, persists a replayable seed plus human-readable CSV exports. Layer 2 clones the canonical seed, applies each delay setting, runs the three algorithms, and writes an aggregate summary that compares delayed parcels against the no-delay baseline for each algorithm.

**Tech Stack:** Python, pytest, existing `env.chengdu` / `experiments.seeding` / algorithm registry utilities, JSON + CSV outputs.

---

### Task 1: Add failing tests for fixed-data export and delayed-parcel summaries

**Files:**
- Create: `tests/test_exp7_fixed_delay_compare.py`
- Modify: `tests/test_exp7_robustness.py`

**Step 1: Write the failing test**

Add focused tests for:
- exporting canonical local parcels and partner task streams to CSV with stable ordering;
- generating delayed local-parcel CSVs with `observed_s_time` shifted only for parcels inside the delay window;
- producing per-delay comparison summaries with:
  - baseline metrics,
  - delayed metrics,
  - metric deltas,
  - affected-parcel transition counts,
  - affected outcome totals before/after delay.
- preserving the same affected parcel id set across algorithms for a given delay spec.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_exp7_fixed_delay_compare.py -q`
Expected: FAIL because the materialization/export/orchestration helpers do not exist yet.

**Step 3: Write minimal implementation**

Add only the helpers required by the tests. Do not change the broader paper sweep flow yet.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_exp7_fixed_delay_compare.py -q`
Expected: PASS.

### Task 2: Implement deterministic Exp-7 data materialization and six-run orchestration

**Files:**
- Create: `experiments/exp7_fixed_delay_compare.py`
- Create: `experiments/run_chengdu_exp7_fixed_delay_compare.py`
- Modify: `experiments/exp7_robustness.py`
- Modify: `experiments/run_chengdu_exp7_deadline_delay.py`
- Modify: `experiments/seeding.py`
- Modify: `algorithms/impgta_runner.py`
- Modify: `baselines/gta.py`

**Step 1: Materialize canonical data**

Implement helpers that:
- build one canonical Chengdu environment from the same CLI config used for the run;
- persist a replayable seed under `Data/delay` (pickle, via existing seed utilities);
- export local parcels to `Data/delay/pick-up-parcels.csv`;
- export partner task streams to stable per-platform CSVs such as `Data/delay/partner-tasks-P1.csv`.

**Step 2: Generate delayed local CSV variants**

Implement helpers that clone the canonical local task list, apply processing delay for `5,10,20,30,60` seconds using the caller-provided delay window, and export:
- `Data/delay/pick-up-parcels-delay-5s.csv`
- `Data/delay/pick-up-parcels-delay-10s.csv`
- `Data/delay/pick-up-parcels-delay-20s.csv`
- `Data/delay/pick-up-parcels-delay-30s.csv`
- `Data/delay/pick-up-parcels-delay-60s.csv`

The export must include both true and observed release times so the perturbation is auditable.

**Step 3: Add ImpGTA decision traces**

Extend the GTA baseline path so `impgta` exposes a `decision_trace` compatible with the existing robustness diff format. This is required because the new summary must compare affected parcels across `capa`, `impgta`, and `ramcom`.

**Step 4: Orchestrate six simulations per algorithm**

Implement a runner that:
- loads or builds the canonical seed;
- runs baseline once per algorithm on the undelayed environment;
- runs each algorithm again for delay values `5,10,20,30,60`;
- stores per-run outputs under the requested output directory;
- aggregates per-delay comparisons against that algorithm’s baseline.

**Step 5: Emit summary centered on affected parcels**

Write `summary.json` with:
- canonical data paths;
- delay window and delay values;
- baseline metrics per algorithm;
- for each algorithm and delay:
  - delayed metrics,
  - metric deltas (`TR`, `CR`, `BPT`, delivered, accepted, timed_out),
  - affected parcel ids/count,
  - transition counts,
  - affected outcome totals before/after delay,
  - paths to the baseline/delayed per-run summaries.

### Task 3: Verify with focused tests and a smoke run

**Files:**
- Test: `tests/test_exp7_fixed_delay_compare.py`
- Test: `tests/test_exp7_robustness.py`
- Test: `tests/test_deadline_disturbance.py`

**Step 1: Run targeted tests**

Run: `pytest tests/test_exp7_fixed_delay_compare.py tests/test_exp7_robustness.py tests/test_deadline_disturbance.py -q`
Expected: PASS.

**Step 2: Run a smoke experiment**

Run:

```bash
python -m experiments.run_chengdu_exp7_fixed_delay_compare \
  --data-dir Data \
  --num-parcels 20 \
  --local-couriers 5 \
  --platforms 2 \
  --couriers-per-platform 3 \
  --task-window-start-seconds 0 \
  --task-window-end-seconds 30 \
  --partner-history-task-count-start 40 \
  --partner-history-task-count-step 0 \
  --batch-size 15 \
  --deadline-seconds 900 \
  --task-sampling-seed 1 \
  --delay-window 10,30 \
  --delay-values 5 10 20 30 60 \
  --algorithms capa impgta ramcom \
  --data-cache-dir Data/delay \
  --output-dir /tmp/exp7_fixed_delay_compare_smoke
```

Expected:
- canonical and delayed CSV files exist under `Data/delay`;
- per-algorithm baseline + delayed run directories exist under `/tmp/exp7_fixed_delay_compare_smoke`;
- aggregate `/tmp/exp7_fixed_delay_compare_smoke/summary.json` exists and contains affected-parcel comparison sections.

**Step 3: Review the final diff**

Check that:
- only the requested algorithms are included by default;
- the delay set is exactly `5,10,20,30,60`;
- the summary compares each delayed run against the same algorithm baseline;
- the affected-parcel analysis uses parcels tagged by the delay window rather than all parcels.
