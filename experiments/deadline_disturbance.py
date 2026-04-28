"""Deadline-disturbance helpers for supplemental Chengdu experiments."""

from __future__ import annotations

from typing import Any, Sequence

from env.chengdu import ChengduEnvironment, get_true_release_time
from experiments.seeding import ChengduEnvironmentSeed, clone_environment_from_seed


DEADLINE_DELAY_AXIS = "deadline_delay"
DEADLINE_DELAY_VALUES = (5, 10, 15, 20, 30, 60)


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
