# Exp-8 Deadline-Noise Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add windowed noise support to Exp-8 deadline-noise experiment, run CAPA sweep for 5000p and 50000p configurations, and summarize results.

**Architecture:** Exp-8 mirrors Exp-7's delay_window pattern: `apply_deadline_noise` gains an optional `window` param that restricts noise to tasks whose true arrival falls inside [start,end]; tasks outside get `observed_d_time = true_deadline` (unnoised). The `--delay-window` CLI arg (already registered) flows through `fixed_config["delay_window"]` and is forwarded to `derive_deadline_noise_environment` in `_derive_paper_environment_for_axis`. Exp-8 script defaults to `("capa",)`.

**Tech Stack:** Python 3.12, pytest, existing Chengdu env + CAPA pipeline, split-mode parallel experiment runner.

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `experiments/deadline_disturbance.py` | Modify | Add `window` param to `apply_deadline_noise` + `derive_deadline_noise_environment` |
| `experiments/paper_chengdu.py` | Modify | Forward `delay_window` to `derive_deadline_noise_environment` for DEADLINE_NOISE_AXIS |
| `experiments/run_chengdu_exp8_deadline_noise.py` | Modify | Fix default algorithms to `("capa",)`, remove dep on exp7 constants |
| `tests/test_deadline_disturbance.py` | Modify | Add windowed-noise tests |

---

### Task 1: Windowed noise in `apply_deadline_noise`

**Files:**
- Modify: `experiments/deadline_disturbance.py`
- Modify: `tests/test_deadline_disturbance.py`

- [ ] **Step 1: Write failing tests**

In `tests/test_deadline_disturbance.py`, add after the existing noise tests:

```python
def test_apply_deadline_noise_window_skips_out_of_window_tasks() -> None:
    """Tasks outside the noise window should get observed_d_time == true deadline."""

    in_window = SimpleNamespace(num="t1", s_time=400.0, d_time=700.0)
    out_of_window = SimpleNamespace(num="t2", s_time=100.0, d_time=500.0)

    apply_deadline_noise([in_window, out_of_window], noise_percent=20, window=(300.0, 600.0))

    slack_in = 700.0 - 400.0  # 300
    assert in_window.observed_d_time == 700.0 + round(300.0 * 0.2)  # 760
    assert in_window.is_noised is True
    assert out_of_window.observed_d_time == 500.0  # no noise
    assert out_of_window.is_noised is False


def test_apply_deadline_noise_window_none_applies_to_all() -> None:
    """When window is None, all tasks receive noise (original behavior)."""

    t1 = SimpleNamespace(num="t1", s_time=10.0, d_time=110.0)
    t2 = SimpleNamespace(num="t2", s_time=500.0, d_time=800.0)

    apply_deadline_noise([t1, t2], noise_percent=10)

    assert t1.observed_d_time == 110.0 + round(100.0 * 0.1)  # 120
    assert t2.observed_d_time == 800.0 + round(300.0 * 0.1)  # 830
```

- [ ] **Step 2: Run tests — expect failure**

```bash
cd /root/code/auction/auction_aware_task_assignment
python -m pytest tests/test_deadline_disturbance.py::test_apply_deadline_noise_window_skips_out_of_window_tasks tests/test_deadline_disturbance.py::test_apply_deadline_noise_window_none_applies_to_all -v 2>&1 | tail -20
```

Expected: FAIL — `apply_deadline_noise` doesn't accept `window` or set `is_noised`.

- [ ] **Step 3: Implement windowed noise in `apply_deadline_noise`**

Replace existing `apply_deadline_noise` in `experiments/deadline_disturbance.py`:

```python
def apply_deadline_noise(
    tasks: Sequence[Any],
    noise_percent: int | float,
    window: tuple[float, float] | None = None,
) -> None:
    """Attach perceived-deadline noise to tasks without mutating ``d_time``.

    Args:
        tasks: Legacy Chengdu task objects to perturb.
        noise_percent: Percentage of each task's true release-to-deadline slack
            added to the model-facing deadline. Negative values make the
            observed deadline earlier.
        window: Optional inclusive ``(start, end)`` true-arrival filter. When
            present, only tasks whose true arrival falls inside the window
            receive noise; remaining tasks get ``observed_d_time`` equal to
            their true deadline. ``True`` is stored in ``is_noised`` for
            affected tasks, ``False`` for the rest.

    Raises:
        ValueError: ``window`` has start greater than end.
    """

    ratio = float(noise_percent) / 100.0
    if window is not None:
        window_start, window_end = float(window[0]), float(window[1])
        if window_start > window_end:
            raise ValueError("noise window start must be <= end.")
    else:
        window_start = window_end = None
    for task in tasks:
        true_release = get_true_release_time(task)
        true_dl = get_true_deadline(task)
        if window is None or (window_start <= true_release <= window_end):
            slack = max(0.0, true_dl - true_release)
            setattr(task, "observed_d_time", true_dl + round(slack * ratio))
            setattr(task, "is_noised", True)
        else:
            setattr(task, "observed_d_time", true_dl)
            setattr(task, "is_noised", False)
```

Also update `derive_deadline_noise_environment` to accept and pass `noise_window`:

```python
def derive_deadline_noise_environment(
    seed: ChengduEnvironmentSeed,
    noise_percent: int | float,
    noise_window: tuple[float, float] | None = None,
) -> ChengduEnvironment:
    """Clone a seed and apply Exp-8 perceived-deadline noise.

    Args:
        seed: Canonical Chengdu environment seed.
        noise_percent: Percent of true deadline slack added to the perceived
            deadline.
        noise_window: Optional inclusive ``(start, end)`` true-arrival filter.
            When present, only tasks whose true arrival falls inside the window
            receive noise.

    Returns:
        Fresh Chengdu environment with `observed_d_time` attached to cloned
        local-platform tasks.
    """

    environment = clone_environment_from_seed(seed)
    apply_deadline_noise(environment.tasks, noise_percent, window=noise_window)
    return environment
```

- [ ] **Step 4: Run tests — expect pass**

```bash
cd /root/code/auction/auction_aware_task_assignment
python -m pytest tests/test_deadline_disturbance.py -v 2>&1 | tail -25
```

Expected: All deadline_disturbance tests PASS.

- [ ] **Step 5: Commit**

```bash
cd /root/code/auction/auction_aware_task_assignment
git add experiments/deadline_disturbance.py tests/test_deadline_disturbance.py
git commit -m "feat(exp8): add windowed noise support to apply_deadline_noise"
```

---

### Task 2: Forward noise_window through paper_chengdu pipeline

**Files:**
- Modify: `experiments/paper_chengdu.py`

- [ ] **Step 1: Update `_derive_paper_environment_for_axis`**

Find the `DEADLINE_NOISE_AXIS` branch in `_derive_paper_environment_for_axis` (around line 1051-1053):

```python
    if axis == DEADLINE_NOISE_AXIS:
        return derive_deadline_noise_environment(seed, value)
```

Replace with:

```python
    if axis == DEADLINE_NOISE_AXIS:
        return derive_deadline_noise_environment(seed, value, noise_window=delay_window)
```

The function signature already accepts `delay_window: tuple[float, float] | None = None` so no change needed there.

- [ ] **Step 2: Verify smoke test passes**

```bash
cd /root/code/auction/auction_aware_task_assignment
python -m pytest tests/test_deadline_disturbance.py -v 2>&1 | tail -15
```

Expected: All PASS.

- [ ] **Step 3: Commit**

```bash
cd /root/code/auction/auction_aware_task_assignment
git add experiments/paper_chengdu.py
git commit -m "fix(exp8): forward delay_window as noise_window in paper axis deriver"
```

---

### Task 3: Fix exp8 script defaults

**Files:**
- Modify: `experiments/run_chengdu_exp8_deadline_noise.py`

- [ ] **Step 1: Rewrite exp8 entrypoint**

Replace the full contents of `experiments/run_chengdu_exp8_deadline_noise.py`:

```python
"""Run Chengdu Exp-8: TR/CR/BPT versus perceived-deadline noise."""

from __future__ import annotations

from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.deadline_disturbance import DEADLINE_NOISE_AXIS
from experiments.paper_chengdu import (
    build_capa_runner_overrides_from_args,
    build_fixed_config_from_args,
    build_script_parser,
    run_chengdu_paper_experiment,
    run_chengdu_paper_point,
    run_chengdu_paper_split_experiment,
)


DEFAULT_EXP8_ALGORITHMS = ("capa",)


def main() -> int:
    """Parse CLI args and launch the deadline-noise robustness experiment."""

    parser = build_script_parser("Run Chengdu experiment 8: metrics versus perceived-deadline noise.")
    parser.set_defaults(algorithms=list(DEFAULT_EXP8_ALGORITHMS))
    args = parser.parse_args()
    fixed_config = build_fixed_config_from_args(args)
    runner_overrides = build_capa_runner_overrides_from_args(args)
    if args.execution_mode == "direct":
        run_chengdu_paper_experiment(
            axis=DEADLINE_NOISE_AXIS,
            output_dir=Path(args.output_dir),
            algorithms=args.algorithms,
            fixed_config_overrides=fixed_config,
            preset_name=args.preset,
            max_workers=args.max_workers,
        )
    elif args.execution_mode == "split":
        run_chengdu_paper_split_experiment(
            axis=DEADLINE_NOISE_AXIS,
            script_path=Path(__file__).resolve(),
            tmp_root=Path(args.tmp_root or "/tmp/chengdu_exp8_deadline_noise_split"),
            output_dir=Path(args.output_dir),
            algorithms=args.algorithms,
            fixed_config_overrides=fixed_config,
            preset_name=args.preset,
            poll_seconds=args.poll_seconds,
            progress_mode=args.progress_mode,
            seed_path=Path(args.seed_path) if args.seed_path else None,
            runner_overrides_by_algorithm=runner_overrides,
        )
    elif args.execution_mode == "point":
        if args.point_value is None:
            raise SystemExit("--point-value is required in point mode.")
        run_chengdu_paper_point(
            axis=DEADLINE_NOISE_AXIS,
            axis_value=float(args.point_value),
            output_dir=Path(args.output_dir),
            algorithms=args.algorithms,
            fixed_config_overrides=fixed_config,
            seed_path=Path(args.seed_path) if args.seed_path else None,
            runner_overrides_by_algorithm=runner_overrides,
        )
    else:
        raise SystemExit(f"Unsupported execution mode for Exp-8: {args.execution_mode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Smoke import check**

```bash
cd /root/code/auction/auction_aware_task_assignment
python -c "from experiments.run_chengdu_exp8_deadline_noise import main; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
cd /root/code/auction/auction_aware_task_assignment
git add experiments/run_chengdu_exp8_deadline_noise.py
git commit -m "fix(exp8): default algorithms to capa-only, remove exp7 dependency"
```

---

### Task 4: Run 5000p CAPA sweep (single seed)

**Files:** outputs only — no code change.

- [ ] **Step 1: Launch split experiment**

```bash
cd /root/code/auction/auction_aware_task_assignment
python -m experiments.run_chengdu_exp8_deadline_noise \
  --execution-mode split \
  --output-dir outputs/plots/exp8_capa_5000p_noise_sweep \
  --tmp-root /tmp/chengdu_exp8_5000p_split \
  --num-parcels 5000 \
  --local-couriers 300 \
  --platforms 4 \
  --couriers-per-platform 50 \
  --task-window-start-seconds 0 \
  --task-window-end-seconds 900 \
  --delay-window 300,600 \
  --partner-history-task-count-start 50000 \
  --partner-history-task-count-step 2000 \
  --algorithms capa \
  --preset formal \
  --progress-mode append \
  2>&1 | tee outputs/plots/exp8_capa_5000p_noise_sweep/run.log
```

- [ ] **Step 2: Verify summary exists**

```bash
cat /root/code/auction/auction_aware_task_assignment/outputs/plots/exp8_capa_5000p_noise_sweep/summary.json | python -m json.tool | head -40
```

Expected: JSON with `sweep_parameter: "deadline_noise"`, 9 runs for noise values -20..20.

---

### Task 5: Run 50000p CAPA sweep (single seed)

**Files:** outputs only — no code change.

- [ ] **Step 1: Launch split experiment**

```bash
cd /root/code/auction/auction_aware_task_assignment
python -m experiments.run_chengdu_exp8_deadline_noise \
  --execution-mode split \
  --output-dir outputs/plots/exp8_capa_50000p_noise_sweep \
  --tmp-root /tmp/chengdu_exp8_50000p_split \
  --num-parcels 50000 \
  --local-couriers 3000 \
  --platforms 4 \
  --couriers-per-platform 200 \
  --task-window-start-seconds 0 \
  --task-window-end-seconds 1800 \
  --delay-window 300,900 \
  --partner-history-task-count-start 50000 \
  --partner-history-task-count-step 2000 \
  --algorithms capa \
  --preset formal \
  --progress-mode append \
  2>&1 | tee outputs/plots/exp8_capa_50000p_noise_sweep/run.log
```

- [ ] **Step 2: Verify summary exists**

```bash
cat /root/code/auction/auction_aware_task_assignment/outputs/plots/exp8_capa_50000p_noise_sweep/summary.json | python -m json.tool | head -40
```

Expected: JSON with `sweep_parameter: "deadline_noise"`, 9 runs for noise values -20..20.

---

### Task 6: Summarize and analyze results

- [ ] **Step 1: Print 5000p results table**

```bash
cd /root/code/auction/auction_aware_task_assignment
python -c "
import json
with open('outputs/plots/exp8_capa_5000p_noise_sweep/summary.json') as f:
    s = json.load(f)
print('5000p CAPA — Deadline Noise Sweep')
print(f'{'noise%':>8}  {'TR':>10}  {'CR':>8}  {'BPT':>10}')
for run in sorted(s['runs'], key=lambda r: r['axis_value']):
    v = run['axis_value']
    m = run['capa']['metrics']
    print(f'{v:>8}  {m[\"TR\"]:>10.2f}  {m[\"CR\"]:>8.4f}  {m[\"BPT\"]:>10.4f}')
"
```

- [ ] **Step 2: Print 50000p results table**

```bash
cd /root/code/auction/auction_aware_task_assignment
python -c "
import json
with open('outputs/plots/exp8_capa_50000p_noise_sweep/summary.json') as f:
    s = json.load(f)
print('50000p CAPA — Deadline Noise Sweep')
print(f'{'noise%':>8}  {'TR':>10}  {'CR':>8}  {'BPT':>10}')
for run in sorted(s['runs'], key=lambda r: r['axis_value']):
    v = run['axis_value']
    m = run['capa']['metrics']
    print(f'{v:>8}  {m[\"TR\"]:>10.2f}  {m[\"CR\"]:>8.4f}  {m[\"BPT\"]:>10.4f}')
"
```

- [ ] **Step 3: Report findings**

Analyze tables for:
- Symmetric degradation: does +20% noise hurt as much as -20%?
- TR direction: positive noise (optimistic deadline) → more feasible assignments → higher TR but lower CR (timeout losses)?
- CR direction: negative noise (pessimistic deadline) → CAPA rejects or crosses more → lower CR on in-window parcels?
- BPT sensitivity vs TR sensitivity.

---

## Self-Review

**Spec coverage:**
- [x] `apply_deadline_noise` gains window param → Task 1
- [x] `derive_deadline_noise_environment` gains noise_window → Task 1
- [x] paper pipeline forwards delay_window to noise deriver → Task 2
- [x] exp8 defaults to `capa` only → Task 3
- [x] 5000p experiment: 300c, 4p, 50cpe, tw 0-900, nw 300-600, step=2000 → Task 4
- [x] 50000p experiment: 3000c, 4p, 200cpe, tw 0-1800, nw 300-900, step=2000 → Task 5
- [x] Results summarized → Task 6
- [x] No RL-CAPA, no multi-seed → tasks 4&5 use single `--algorithms capa`

**Placeholder scan:** None found.

**Type consistency:** `window: tuple[float, float] | None` used consistently across `apply_deadline_noise` and `derive_deadline_noise_environment`.
