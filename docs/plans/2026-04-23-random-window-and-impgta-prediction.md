# Random Window Sampling and ImpGTA Prediction-Confidence Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace Chengdu parcel selection from deterministic time-prefix truncation with deterministic random sampling inside a user-specified time window, and add prediction-success modeling to ImpGTA's future-window logic while keeping the unified environment and experiment flow consistent across all algorithms.

**Architecture:** The parcel-window change belongs in the unified Chengdu environment build path so every algorithm consumes the same sampled task stream. The ImpGTA change stays inside the GTA baseline logic, but its parameters must flow through the same runner/experiment configuration chain used by the rest of the repository.

**Tech Stack:** Python 3, unittest, argparse, unified Chengdu environment (`env/chengdu.py`), experiment framework (`experiments/*`), GTA baselines (`baselines/gta.py`).

---

### Task 1: Add failing tests for parcel time-window sampling

**Files:**
- Modify: `tests/test_metric_alignment.py`
- Modify: `env/chengdu.py`

**Step 1: Write failing tests**

Add tests covering:
- task selection uses only tasks within `[window_start, window_end]`
- selection is deterministic for a fixed sampling seed
- selection is not prefix truncation when more tasks exist in the window than requested
- requesting more parcels than available in the window raises a clear `ValueError`

**Step 2: Run tests to verify failure**

Run:
```bash
python3 -m unittest tests.test_metric_alignment.MetricAlignmentTest.test_select_station_pick_tasks_samples_within_window -v
python3 -m unittest tests.test_metric_alignment.MetricAlignmentTest.test_select_station_pick_tasks_rejects_window_underflow -v
```

**Step 3: Implement minimal environment support**

Modify `env/chengdu.py` to:
- introduce optional `task_window_start_seconds`, `task_window_end_seconds`, `task_sampling_seed`
- filter ordered pick tasks by time window before station assignment
- randomly sample `num_parcels` from the filtered set using a dedicated `random.Random(seed)`
- sort sampled tasks back by legacy task order before returning so downstream arrival logic stays coherent
- validate the requested window against the dataset min/max task times

**Step 4: Run tests to verify pass**

Run the two tests above again, then:
```bash
python3 -m unittest tests.test_metric_alignment -v
```

**Step 5: Commit**

```bash
git add docs/plans/2026-04-23-random-window-and-impgta-prediction.md tests/test_metric_alignment.py env/chengdu.py
git commit -m "feat(env): sample parcels within a configured time window"
```

### Task 2: Propagate window-sampling parameters through unified config and experiment entrypoints

**Files:**
- Modify: `experiments/config.py`
- Modify: `experiments/paper_chengdu.py`
- Modify: `experiments/seeding.py`
- Modify: `runner.py`
- Modify: `experiments/compare.py`
- Modify: `experiments/sweep.py`
- Modify: `experiments/run_chengdu_exp1_num_parcels.py`
- Modify: `experiments/run_chengdu_exp2_couriers.py`
- Modify: `experiments/run_chengdu_exp3_radius.py`
- Modify: `experiments/run_chengdu_exp4_platforms.py`
- Modify: `experiments/run_chengdu_exp5_default_compare.py`
- Modify: `experiments/run_chengdu_exp6_capacity.py`
- Modify: `README.md`
- Test: `tests/test_metric_alignment.py`

**Step 1: Write failing tests**

Add tests covering:
- `ExperimentConfig.as_environment_kwargs()` includes the new window args
- `build_fixed_config_from_args()` carries the new CLI parameters
- canonical environment seed capture/clone preserves the task-window config

**Step 2: Run tests to verify failure**

Run:
```bash
python3 -m unittest tests.test_metric_alignment.MetricAlignmentTest.test_experiment_config_carries_task_window_sampling -v
python3 -m unittest tests.test_metric_alignment.MetricAlignmentTest.test_environment_seed_preserves_task_window_sampling -v
```

**Step 3: Implement parameter propagation**

Wire the new parameters through:
- root runner common args
- paper experiment script parser/build_fixed_config
- `ExperimentConfig`
- canonical seed build/clone/save/load
- point/split command builders
- README command documentation

**Step 4: Run tests to verify pass**

Run:
```bash
python3 -m unittest tests.test_metric_alignment -v
python3 -m py_compile env/chengdu.py experiments/config.py experiments/paper_chengdu.py experiments/seeding.py runner.py
```

**Step 5: Commit**

```bash
git add tests/test_metric_alignment.py experiments/config.py experiments/paper_chengdu.py experiments/seeding.py runner.py experiments/run_chengdu_exp1_num_parcels.py experiments/run_chengdu_exp2_couriers.py experiments/run_chengdu_exp3_radius.py experiments/run_chengdu_exp4_platforms.py experiments/run_chengdu_exp5_default_compare.py experiments/run_chengdu_exp6_capacity.py experiments/compare.py experiments/sweep.py README.md
git commit -m "feat(experiments): wire parcel window sampling through unified entrypoints"
```

### Task 3: Add failing tests for ImpGTA prediction-success modeling

**Files:**
- Modify: `tests/test_metric_alignment.py`
- Modify: `baselines/gta.py`

**Step 1: Write failing tests**

Add tests covering:
- prediction success rate `1.0` preserves the current future-window behavior
- prediction success rate `0.0` removes future-window support entirely
- intermediate success rate produces a deterministic reduced future set under a fixed seed
- inner and outer ImpGTA condition checks use the predicted subset rather than the full real future list

**Step 2: Run tests to verify failure**

Run:
```bash
python3 -m unittest tests.test_metric_alignment.MetricAlignmentTest.test_impgta_prediction_success_rate_controls_future_window -v
python3 -m unittest tests.test_metric_alignment.MetricAlignmentTest.test_impgta_zero_success_rate_removes_future_signal -v
```

**Step 3: Implement minimal ImpGTA prediction-success logic**

Modify `baselines/gta.py` to:
- add `prediction_success_rate` and `prediction_sampling_seed`
- transform the real future-window task list into a deterministic predicted subset
- keep BaseGTA behavior unchanged
- keep AIM and matching mechanics unchanged
- reuse the predicted subset in both inner and outer ImpGTA conditions

**Step 4: Run tests to verify pass**

Run:
```bash
python3 -m unittest tests.test_metric_alignment -v
python3 -m py_compile baselines/gta.py
```

**Step 5: Commit**

```bash
git add tests/test_metric_alignment.py baselines/gta.py
git commit -m "feat(impgta): model prediction success in future-window decisions"
```

### Task 4: Propagate ImpGTA prediction-success parameters through runners and experiments

**Files:**
- Modify: `experiments/config.py`
- Modify: `experiments/paper_chengdu.py`
- Modify: `runner.py`
- Modify: `experiments/compare.py`
- Modify: `experiments/sweep.py`
- Modify: `README.md`
- Test: `tests/test_metric_alignment.py`

**Step 1: Write failing tests**

Add tests covering:
- unified runner kwargs for `impgta` include the new prediction-success fields
- paper fixed config carries them
- compare/sweep config reconstruction passes them into `ExperimentConfig`

**Step 2: Run tests to verify failure**

Run:
```bash
python3 -m unittest tests.test_metric_alignment.MetricAlignmentTest.test_runner_builds_impgta_prediction_success_kwargs -v
```

**Step 3: Implement propagation**

Extend CLI/config plumbing with:
- `--prediction-success-rate`
- `--prediction-sampling-seed`

**Step 4: Run tests to verify pass**

Run:
```bash
python3 -m unittest tests.test_metric_alignment -v
python3 -m py_compile experiments/config.py experiments/paper_chengdu.py runner.py experiments/compare.py experiments/sweep.py
```

**Step 5: Commit**

```bash
git add tests/test_metric_alignment.py experiments/config.py experiments/paper_chengdu.py runner.py experiments/compare.py experiments/sweep.py README.md
git commit -m "feat(impgta): expose prediction-success controls in unified experiments"
```

### Task 5: Run smoke verification on the unified experiment flow

**Files:**
- No new source files unless fixes are required by verification

**Step 1: Run targeted smoke checks**

Run:
```bash
python3 experiments/run_chengdu_exp1_num_parcels.py --execution-mode point --point-value 20 --output-dir /tmp/chengdu_exp1_window_smoke --algorithms capa greedy impgta --data-dir Data --num-parcels 20 --local-couriers 8 --platforms 1 --couriers-per-platform 2 --batch-size 30 --task-window-start-seconds 0 --task-window-end-seconds 3600 --task-sampling-seed 7 --prediction-success-rate 0.5 --prediction-sampling-seed 11
python3 experiments/run_chengdu_exp2_couriers.py --execution-mode point --point-value 8 --output-dir /tmp/chengdu_exp2_window_smoke --algorithms capa impgta --data-dir Data --num-parcels 20 --local-couriers 8 --platforms 1 --couriers-per-platform 2 --batch-size 30 --task-window-start-seconds 0 --task-window-end-seconds 3600 --task-sampling-seed 7 --prediction-success-rate 0.5 --prediction-sampling-seed 11
```

**Step 2: Verify expected outputs**

Check:
- both commands produce `summary.json`
- the task-window options are accepted by the formal scripts
- ImpGTA runs with the new prediction-success options

**Step 3: Final status review**

Run:
```bash
git status --short
```

