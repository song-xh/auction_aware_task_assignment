"""Deadline-disturbance helpers for supplemental Chengdu experiments."""

from __future__ import annotations

from typing import Any, Sequence

from env.chengdu import ChengduEnvironment, get_true_deadline, get_true_release_time
from experiments.seeding import ChengduEnvironmentSeed, clone_environment_from_seed


DEADLINE_DELAY_AXIS = "deadline_delay"
DEADLINE_DELAY_VALUES = (5, 10, 15, 20, 30, 60)
DEADLINE_NOISE_AXIS = "deadline_noise"
DEADLINE_NOISE_VALUES = (-20, -15, -10, -5, 0, 5, 10, 15, 20)


def apply_processing_delay(
    tasks: Sequence[Any],
    delay_seconds: int | float,
    window: tuple[float, float] | None = None,
) -> None:
    """Attach observed release-time delay to tasks without mutating originals.

    Args:
        tasks: Legacy Chengdu task objects to perturb.
        delay_seconds: Processing delay in seconds added after true arrival.
        window: Optional inclusive ``(start, end)`` true-arrival filter. When
            present, only tasks whose true arrival falls inside the window
            receive the delay; remaining tasks keep their original observed
            release time. ``True`` is stored in ``is_delayed`` for affected
            tasks, ``False`` for the rest.

    Raises:
        ValueError: ``delay_seconds`` is negative, or ``window`` has start
            greater than end.
    """

    delay = float(delay_seconds)
    if delay < 0:
        raise ValueError("delay_seconds must be non-negative.")
    if window is not None:
        window_start, window_end = float(window[0]), float(window[1])
        if window_start > window_end:
            raise ValueError("delay window start must be <= end.")
    else:
        window_start = window_end = None
    for task in tasks:
        true_arrival = get_true_release_time(task)
        if window is None or (window_start <= true_arrival <= window_end):
            setattr(task, "observed_s_time", true_arrival + delay)
            setattr(task, "is_delayed", True)
        else:
            setattr(task, "observed_s_time", true_arrival)
            setattr(task, "is_delayed", False)


def derive_deadline_delay_environment(
    seed: ChengduEnvironmentSeed,
    delay_seconds: int | float,
    window: tuple[float, float] | None = None,
) -> ChengduEnvironment:
    """Clone a seed and apply Exp-7 processing-delay disturbance.

    Args:
        seed: Canonical Chengdu environment seed.
        delay_seconds: Processing delay in seconds.
        window: Optional ``(start, end)`` true-arrival filter passed through to
            :func:`apply_processing_delay`.

    Returns:
        Fresh Chengdu environment with `observed_s_time` and `is_delayed`
        attached to cloned local-platform tasks.
    """

    environment = clone_environment_from_seed(seed)
    apply_processing_delay(environment.tasks, delay_seconds, window=window)
    return environment


def parse_delay_window(spec: str) -> tuple[float, float]:
    """Parse a ``START,END`` window specifier from the CLI into a numeric pair.

    Args:
        spec: ``"start,end"`` string with float-parseable bounds.

    Returns:
        ``(start, end)`` tuple with ``start <= end``.

    Raises:
        ValueError: When the spec is malformed or bounds are inverted.
    """

    parts = [part.strip() for part in spec.split(",")]
    if len(parts) != 2:
        raise ValueError(f"--delay-window must be `start,end`, got {spec!r}.")
    start, end = float(parts[0]), float(parts[1])
    if start > end:
        raise ValueError(f"--delay-window start ({start}) must be <= end ({end}).")
    return start, end


def apply_deadline_noise(tasks: Sequence[Any], noise_percent: int | float) -> None:
    """Attach perceived-deadline noise to tasks without mutating ``d_time``.

    Args:
        tasks: Legacy Chengdu task objects to perturb.
        noise_percent: Percentage of each task's true release-to-deadline slack
            added to the model-facing deadline. Negative values make the
            observed deadline earlier.
    """

    ratio = float(noise_percent) / 100.0
    for task in tasks:
        slack = max(0.0, get_true_deadline(task) - get_true_release_time(task))
        setattr(task, "observed_d_time", get_true_deadline(task) + round(slack * ratio))


def derive_deadline_noise_environment(
    seed: ChengduEnvironmentSeed,
    noise_percent: int | float,
) -> ChengduEnvironment:
    """Clone a seed and apply Exp-8 perceived-deadline noise.

    Args:
        seed: Canonical Chengdu environment seed.
        noise_percent: Percent of true deadline slack added to the perceived
            deadline.

    Returns:
        Fresh Chengdu environment with `observed_d_time` attached to cloned
        local-platform tasks.
    """

    environment = clone_environment_from_seed(seed)
    apply_deadline_noise(environment.tasks, noise_percent)
    return environment
