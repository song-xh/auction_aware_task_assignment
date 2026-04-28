# Deadline Disturbance Experiments Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Exp-7 deadline processing-delay and Exp-8 perceived-deadline noise experiments comparing retrained `rl-capa` against `ramcom`.

**Architecture:** Add a shared disturbance layer that injects temporary observed time fields into cloned task objects while preserving original `d_time` as the true deadline. Wire new axes into the existing Chengdu paper experiment framework so direct, split, and point modes reuse seeded environments, progress reporting, summaries, and plotting.

**Tech Stack:** Python, argparse, unittest/pytest, existing Chengdu experiment framework, existing RL-CAPA runner, matplotlib plotting utilities.

---

### Task 1: Add Shared Observed-Time Accessors And Tests

**Files:**
- Modify: `env/chengdu.py`
- Modify: `baselines/common.py`
- Modify: `baselines/ramcom.py`
- Modify: `rl_capa/env.py`
- Create: `tests/test_deadline_disturbance.py`

**Step 1: Write failing tests**

Add tests that create lightweight `SimpleNamespace` tasks and assert:

```python
def test_observed_time_helpers_preserve_true_deadline():
    task = SimpleNamespace(num="t1", s_time=10.0, d_time=100.0, observed_s_time=15.0, observed_d_time=80.0)
    assert get_model_release_time(task) == 15.0
    assert get_model_deadline(task) == 80.0
    assert get_true_deadline(task) == 100.0


def test_legacy_task_to_parcel_can_use_observed_deadline():
    task = SimpleNamespace(num="t1", s_time=10.0, d_time=100.0, observed_d_time=80.0, weight=1.0, fare=20.0, l_node="A")
    assert legacy_task_to_parcel(task).deadline == 80
    assert legacy_task_to_parcel(task, use_observed_deadline=False).deadline == 100
```

Also add a batch test proving `prepare_chengdu_batch` uses `observed_s_time` for arrival visibility but true `d_time` for expiration.

**Step 2: Run tests to verify failure**

Run:

```bash
python3 -m pytest tests/test_deadline_disturbance.py -q
```

Expected: FAIL because the helper functions and observed-field support do not exist yet.

**Step 3: Implement shared helpers**

In `env/chengdu.py`, add public helper functions with docstrings and type annotations:

```python
def get_model_release_time(task: Any) -> float:
    """Return the algorithm-facing task release time, using observed_s_time when present."""


def get_true_release_time(task: Any) -> float:
    """Return the original task release time stored in s_time."""


def get_model_deadline(task: Any) -> float:
    """Return the algorithm-facing task deadline, using observed_d_time when present."""


def get_true_deadline(task: Any) -> float:
    """Return the original task deadline stored in d_time."""
```

Update:

- `sort_legacy_tasks()` and task sorting paths to use model release/deadline for algorithm order.
- `legacy_task_to_parcel(task, use_observed_deadline: bool = True)` to select observed or true deadline.
- `prepare_chengdu_batch()` arrival collection to use model release time.
- `prepare_chengdu_batch()` true-expired split to use `get_true_deadline()`.
- Current batch parcel conversion, RL-CAPA state building, and baseline feasible insertion helpers to use observed deadline by default.

Do not add fallback/degradation logic. Missing `s_time` or `d_time` should still fail normally.

**Step 4: Run tests to verify pass**

Run:

```bash
python3 -m pytest tests/test_deadline_disturbance.py tests/test_metric_alignment.py::MetricAlignmentTests::test_greedy_summary_uses_delivered_completion_rate -q
```

Expected: PASS.

**Step 5: Do not commit yet**

This shared support is committed with Exp-7 after the first experiment is fully wired and verified.

---

### Task 2: Implement Exp-7 Deadline Processing Delay

**Files:**
- Create: `experiments/deadline_disturbance.py`
- Modify: `experiments/config.py`
- Modify: `experiments/paper_config.py`
- Modify: `experiments/paper_chengdu.py`
- Create: `experiments/run_chengdu_exp7_deadline_delay.py`
- Modify: `tests/test_deadline_disturbance.py`

**Step 1: Extend failing tests**

Add tests for:

```python
def test_apply_deadline_delay_sets_observed_release_only():
    task = SimpleNamespace(num="t1", s_time=10.0, d_time=100.0)
    apply_processing_delay([task], delay_seconds=20)
    assert task.s_time == 10.0
    assert task.d_time == 100.0
    assert task.observed_s_time == 30.0
```

Add a point-level test for deriving a delay environment from an in-memory seed.

**Step 2: Run tests to verify failure**

Run:

```bash
python3 -m pytest tests/test_deadline_disturbance.py -q
```

Expected: FAIL because Exp-7 helpers/axis are missing.

**Step 3: Implement disturbance helper module**

In `experiments/deadline_disturbance.py`, implement:

```python
DEADLINE_DELAY_AXIS = "deadline_delay"
DEADLINE_DELAY_VALUES = (5, 10, 15, 20, 30, 60)

def apply_processing_delay(tasks: Sequence[Any], delay_seconds: int | float) -> None:
    """Attach observed_s_time to each task without mutating s_time or d_time."""


def derive_deadline_delay_environment(seed: ChengduEnvironmentSeed, delay_seconds: int | float) -> ChengduEnvironment:
    """Clone a seed and apply processing-delay disturbance to the cloned tasks."""
```

Use `clone_environment_from_seed(seed)` and mutate only cloned task objects.

**Step 4: Wire Exp-7 axis**

Update:

- `SUPPORTED_SWEEP_AXES` and `apply_sweep_axis()` for `deadline_delay`.
- `PAPER_SUITE_PRESETS["chengdu-paper"]` with smoke and formal delay values.
- `_experiment_label_for_axis()` to return `Exp-7`.
- `_canonical_environment_kwargs_for_axis()` to accept `deadline_delay` without changing canonical size.
- `run_chengdu_paper_point()` and seeded point deriver to call `derive_deadline_delay_environment()` for this axis.
- `run_chengdu_paper_split_experiment()` aggregation and manifest continue to produce `tr_vs_deadline_delay.png`, `cr_vs_deadline_delay.png`, and `bpt_vs_deadline_delay.png`.

**Step 5: Add CLI wrapper**

Create `experiments/run_chengdu_exp7_deadline_delay.py` modeled after Exp-6, with default algorithms:

```python
DEFAULT_DEADLINE_DISTURBANCE_ALGORITHMS = ("rl-capa", "ramcom")
```

Support `direct`, `split`, and `point` execution modes. Default split tmp root: `/tmp/chengdu_exp7_deadline_delay_split`.

**Step 6: Verify Exp-7**

Run:

```bash
python3 -m pytest tests/test_deadline_disturbance.py tests/test_progress_io.py -q
```

Run a small direct CLI smoke:

```bash
python3 experiments/run_chengdu_exp7_deadline_delay.py \
  --execution-mode direct \
  --output-dir /tmp/exp7_deadline_delay_smoke \
  --preset smoke \
  --algorithms ramcom \
  --data-dir Data \
  --num-parcels 20 \
  --local-couriers 2 \
  --platforms 1 \
  --couriers-per-platform 2 \
  --courier-capacity 20 \
  --task-window-start-seconds 0 \
  --task-window-end-seconds 60
```

Expected: command exits 0 and writes `/tmp/exp7_deadline_delay_smoke/summary.json` plus `tr_vs_deadline_delay.png`.

**Step 7: Commit Exp-7**

Run:

```bash
git add env/chengdu.py baselines/common.py baselines/ramcom.py rl_capa/env.py experiments/deadline_disturbance.py experiments/config.py experiments/paper_config.py experiments/paper_chengdu.py experiments/run_chengdu_exp7_deadline_delay.py tests/test_deadline_disturbance.py
git commit -m "experiment: add deadline delay robustness experiment"
```

---

### Task 3: Implement Exp-8 Deadline Noise

**Files:**
- Modify: `experiments/deadline_disturbance.py`
- Modify: `experiments/config.py`
- Modify: `experiments/paper_config.py`
- Modify: `experiments/paper_chengdu.py`
- Create: `experiments/run_chengdu_exp8_deadline_noise.py`
- Modify: `tests/test_deadline_disturbance.py`

**Step 1: Extend failing tests**

Add tests:

```python
def test_apply_deadline_noise_uses_slack_and_preserves_true_deadline():
    task = SimpleNamespace(num="t1", s_time=10.0, d_time=110.0)
    apply_deadline_noise([task], noise_percent=20)
    assert task.d_time == 110.0
    assert task.observed_d_time == 130.0
```

Also test `noise_percent=-20` yields `observed_d_time == 90.0`.

**Step 2: Run tests to verify failure**

Run:

```bash
python3 -m pytest tests/test_deadline_disturbance.py -q
```

Expected: FAIL because Exp-8 helpers/axis are missing.

**Step 3: Implement noise helpers**

In `experiments/deadline_disturbance.py`, add:

```python
DEADLINE_NOISE_AXIS = "deadline_noise"
DEADLINE_NOISE_VALUES = (-20, -15, -10, -5, 0, 5, 10, 15, 20)

def apply_deadline_noise(tasks: Sequence[Any], noise_percent: int | float) -> None:
    """Attach observed_d_time based on deadline slack without mutating d_time."""


def derive_deadline_noise_environment(seed: ChengduEnvironmentSeed, noise_percent: int | float) -> ChengduEnvironment:
    """Clone a seed and apply perceived-deadline noise to the cloned tasks."""
```

Use `round(max(0.0, d_time - s_time) * noise_percent / 100.0)`.

**Step 4: Wire Exp-8 axis**

Update:

- `SUPPORTED_SWEEP_AXES` and `apply_sweep_axis()` for `deadline_noise`.
- `PAPER_SUITE_PRESETS["chengdu-paper"]` with smoke and formal noise values.
- `_experiment_label_for_axis()` to return `Exp-8`.
- `_canonical_environment_kwargs_for_axis()` to accept `deadline_noise`.
- `run_chengdu_paper_point()` seeded environment deriver to call `derive_deadline_noise_environment()`.

**Step 5: Add CLI wrapper**

Create `experiments/run_chengdu_exp8_deadline_noise.py` modeled after Exp-7. Default split tmp root: `/tmp/chengdu_exp8_deadline_noise_split`.

**Step 6: Verify Exp-8**

Run:

```bash
python3 -m pytest tests/test_deadline_disturbance.py tests/test_progress_io.py -q
```

Run a small direct CLI smoke:

```bash
python3 experiments/run_chengdu_exp8_deadline_noise.py \
  --execution-mode direct \
  --output-dir /tmp/exp8_deadline_noise_smoke \
  --preset smoke \
  --algorithms ramcom \
  --data-dir Data \
  --num-parcels 20 \
  --local-couriers 2 \
  --platforms 1 \
  --couriers-per-platform 2 \
  --courier-capacity 20 \
  --task-window-start-seconds 0 \
  --task-window-end-seconds 60
```

Expected: command exits 0 and writes `/tmp/exp8_deadline_noise_smoke/summary.json` plus `tr_vs_deadline_noise.png`.

**Step 7: Commit Exp-8**

Run:

```bash
git add experiments/deadline_disturbance.py experiments/config.py experiments/paper_config.py experiments/paper_chengdu.py experiments/run_chengdu_exp8_deadline_noise.py tests/test_deadline_disturbance.py
git commit -m "experiment: add deadline noise robustness experiment"
```

---

### Task 4: Final Regression Verification

**Files:**
- No required source changes unless verification exposes a defect.

**Step 1: Run focused regression tests**

Run:

```bash
python3 -m pytest tests/test_deadline_disturbance.py tests/test_rl_runner_ux.py tests/test_rl_output_artifacts.py tests/test_progress_io.py -q
```

Expected: PASS.

**Step 2: Run parser smoke checks**

Run:

```bash
python3 experiments/run_chengdu_exp7_deadline_delay.py --help
python3 experiments/run_chengdu_exp8_deadline_noise.py --help
```

Expected: both commands exit 0 and show shared Chengdu paper arguments.

**Step 3: Check git status**

Run:

```bash
git status --short
```

Expected: clean working tree after the two experiment commits.

**Step 4: Report completion**

Summarize:

- Exp-7 CLI and output paths.
- Exp-8 CLI and output paths.
- Tests and smoke commands run.
- Any known limitation, especially that full formal runs retrain RL-CAPA at every point and may take substantial time.
