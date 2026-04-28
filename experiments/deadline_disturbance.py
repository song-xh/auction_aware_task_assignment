"""Deadline-disturbance helpers for supplemental Chengdu experiments."""

from __future__ import annotations

from typing import Any, Sequence

from env.chengdu import ChengduEnvironment, get_true_deadline, get_true_release_time
from experiments.seeding import ChengduEnvironmentSeed, clone_environment_from_seed


DEADLINE_DELAY_AXIS = "deadline_delay"
DEADLINE_DELAY_VALUES = (5, 10, 15, 20, 30, 60)
DEADLINE_NOISE_AXIS = "deadline_noise"
DEADLINE_NOISE_VALUES = (-20, -15, -10, -5, 0, 5, 10, 15, 20)


def apply_processing_delay(tasks: Sequence[Any], delay_seconds: int | float) -> None:
    """Attach observed release-time delay to tasks without mutating originals.

    Args:
        tasks: Legacy Chengdu task objects to perturb.
        delay_seconds: Processing delay in seconds applied after true arrival.

    Raises:
        ValueError: If `delay_seconds` is negative.
    """

    delay = float(delay_seconds)
    if delay < 0:
        raise ValueError("delay_seconds must be non-negative.")
    for task in tasks:
        setattr(task, "observed_s_time", get_true_release_time(task) + delay)


def derive_deadline_delay_environment(
    seed: ChengduEnvironmentSeed,
    delay_seconds: int | float,
) -> ChengduEnvironment:
    """Clone a seed and apply Exp-7 processing-delay disturbance.

    Args:
        seed: Canonical Chengdu environment seed.
        delay_seconds: Processing delay in seconds.

    Returns:
        Fresh Chengdu environment with `observed_s_time` attached to cloned
        local-platform tasks.
    """

    environment = clone_environment_from_seed(seed)
    apply_processing_delay(environment.tasks, delay_seconds)
    return environment


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
