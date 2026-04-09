"""Generic point-level seeded experiment runner shared by experiment wrappers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Mapping

from algorithms.registry import build_algorithm_runner
from capa.config import DEFAULT_IMPGTA_WINDOW_SECONDS
from experiments.progress import build_point_progress_snapshot, write_point_progress
from experiments.seeding import build_environment_seed, clone_environment_from_seed, load_environment_seed

from .models import ExperimentPointSpec


def default_runner_kwargs_for_algorithm(
    algorithm: str,
    batch_size: int,
    overrides: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build default runner kwargs for one algorithm.

    Args:
        algorithm: Canonical algorithm name.
        batch_size: Shared batch size in seconds.
        overrides: Optional algorithm-specific overrides.

    Returns:
        Runner kwargs for the requested algorithm.
    """

    kwargs: dict[str, Any] = {}
    if algorithm in {"capa", "greedy", "mra"}:
        kwargs["batch_size"] = batch_size
    elif algorithm == "impgta":
        kwargs["prediction_window_seconds"] = DEFAULT_IMPGTA_WINDOW_SECONDS
    if overrides and algorithm in overrides:
        kwargs.update(dict(overrides[algorithm]))
    return kwargs


def run_seeded_comparison_point(
    seed_path: Path,
    point_spec: ExperimentPointSpec,
    environment_deriver: Callable[[Any, int | float], Any],
    runner_builder: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Run one comparison point from a persisted canonical environment seed.

    Args:
        seed_path: Canonical seed bundle path.
        point_spec: Point-level experiment specification.
        environment_deriver: Callback that derives one environment from the seed and axis value.
        runner_builder: Optional algorithm runner factory.

    Returns:
        Point-level normalized summary.
    """

    seed = load_environment_seed(seed_path)
    point_environment = environment_deriver(seed, point_spec.axis_value)
    point_spec.output_dir.mkdir(parents=True, exist_ok=True)
    return run_environment_comparison_point(
        environment=point_environment,
        point_spec=point_spec,
        runner_builder=runner_builder,
    )


def run_environment_comparison_point(
    environment: Any,
    point_spec: ExperimentPointSpec,
    runner_builder: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Run one comparison point from an already built environment.

    Args:
        environment: Prepared mutable environment for the current sweep point.
        point_spec: Point-level experiment specification.
        runner_builder: Optional algorithm runner factory.

    Returns:
        Point-level normalized summary.
    """

    point_seed = build_environment_seed(environment)
    point_spec.output_dir.mkdir(parents=True, exist_ok=True)
    return _run_point_from_seed(point_seed=point_seed, point_spec=point_spec, runner_builder=runner_builder)


def _run_point_from_seed(
    point_seed: Any,
    point_spec: ExperimentPointSpec,
    runner_builder: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Execute one point from a prepared in-memory seed.

    Args:
        point_seed: Seed object previously built from an environment.
        point_spec: Point-level experiment specification.
        runner_builder: Optional algorithm runner factory.

    Returns:
        Point-level normalized summary.
    """

    build_runner = runner_builder or build_algorithm_runner
    progress_path = point_spec.output_dir / "progress.json"
    point_summary: dict[str, Any] = {point_spec.axis_name: point_spec.axis_value}
    completed_algorithms: list[str] = []
    total_algorithms = len(point_spec.algorithms)
    for algorithm_index, algorithm in enumerate(point_spec.algorithms, start=1):
        runner = build_runner(
            algorithm,
            **default_runner_kwargs_for_algorithm(
                algorithm=algorithm,
                batch_size=point_spec.batch_size,
                overrides=point_spec.runner_overrides_by_algorithm,
            ),
        )
        last_event: dict[str, Any] = {}

        def progress_callback(event: dict[str, Any]) -> None:
            """Persist one live progress event emitted by the active algorithm."""

            nonlocal last_event
            last_event = dict(event)
            write_point_progress(
                progress_path,
                build_point_progress_snapshot(
                    axis_name=point_spec.axis_name,
                    axis_value=point_spec.axis_value,
                    algorithm=algorithm,
                    algorithm_index=algorithm_index,
                    total_algorithms=total_algorithms,
                    completed_algorithms=completed_algorithms,
                    state="running",
                    last_event=last_event,
                ),
            )

        write_point_progress(
            progress_path,
            build_point_progress_snapshot(
                axis_name=point_spec.axis_name,
                axis_value=point_spec.axis_value,
                algorithm=algorithm,
                algorithm_index=algorithm_index,
                total_algorithms=total_algorithms,
                completed_algorithms=completed_algorithms,
                state="running",
                last_event={"phase": "starting", "detail": f"starting {algorithm}"},
            ),
        )
        point_summary[algorithm] = runner.run(
            environment=clone_environment_from_seed(point_seed),
            output_dir=point_spec.output_dir / algorithm,
            progress_callback=progress_callback,
        )
        completed_algorithms.append(algorithm)
        write_point_progress(
            progress_path,
            build_point_progress_snapshot(
                axis_name=point_spec.axis_name,
                axis_value=point_spec.axis_value,
                algorithm=algorithm,
                algorithm_index=algorithm_index,
                total_algorithms=total_algorithms,
                completed_algorithms=completed_algorithms,
                state="finished" if algorithm_index == total_algorithms else "running",
                last_event=last_event or {"phase": "completed", "detail": f"completed {algorithm}"},
            ),
        )
    with (point_spec.output_dir / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(point_summary, handle, indent=2)
    return point_summary
