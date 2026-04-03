"""Comparison sweep orchestration with shared Chengdu environment seeds."""

from __future__ import annotations

import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any, Callable, Sequence

from algorithms.registry import build_algorithm_runner
from env.chengdu import ChengduEnvironment

from .config import ExperimentConfig, apply_sweep_axis
from .plotting import save_comparison_plots
from .seeding import build_environment_seed, clone_environment_from_seed


def run_comparison_sweep(
    algorithms: Sequence[str],
    output_dir: Path,
    sweep_parameter: str,
    sweep_values: Sequence[int],
    fixed_config: dict[str, Any],
    environment_builder: Callable[..., ChengduEnvironment] | None = None,
    runner_builder: Callable[..., Any] | None = None,
    max_workers: int | None = None,
) -> dict[str, Any]:
    """Run a shared-environment comparison sweep and persist a normalized summary.

    Args:
        algorithms: Algorithm names to compare at each sweep point.
        output_dir: Directory that receives the aggregate summary.
        sweep_parameter: Parameter varied across the sweep.
        sweep_values: Ordered values explored on the chosen axis.
        fixed_config: Base configuration shared across the sweep.
        environment_builder: Optional injected environment builder for tests.
        runner_builder: Optional injected algorithm runner builder for tests.

    Returns:
        A normalized comparison summary keyed by run and algorithm.
    """

    builder = environment_builder or ChengduEnvironment.build
    build_runner = runner_builder or build_algorithm_runner
    output_dir.mkdir(parents=True, exist_ok=True)
    runs: list[dict[str, Any]] = []

    base_config = ExperimentConfig(
        data_dir=Path(fixed_config["data_dir"]),
        num_parcels=fixed_config.get("num_parcels", 100),
        local_couriers=fixed_config.get("local_couriers", 10),
        platforms=fixed_config.get("platforms", 2),
        couriers_per_platform=fixed_config.get("couriers_per_platform", 5),
        batch_size=fixed_config.get("batch_size", 300),
        prediction_window_seconds=fixed_config.get("prediction_window_seconds", 180),
        service_radius_km=fixed_config.get("service_radius_km"),
        courier_capacity=fixed_config.get("courier_capacity"),
        extra=dict(fixed_config.get("extra", {})),
    )

    if max_workers is not None and max_workers > 1 and environment_builder is None and runner_builder is None and len(sweep_values) > 1:
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(
                    _run_comparison_point,
                    algorithms=tuple(algorithms),
                    sweep_parameter=sweep_parameter,
                    value=value,
                    fixed_config=dict(fixed_config),
                    output_dir=output_dir,
                )
                for value in sweep_values
            ]
            runs = [future.result() for future in futures]
            runs.sort(key=lambda item: item[sweep_parameter])
    else:
        for value in sweep_values:
            runs.append(
                _run_comparison_point(
                    algorithms=algorithms,
                    sweep_parameter=sweep_parameter,
                    value=value,
                    fixed_config=fixed_config,
                    output_dir=output_dir,
                    environment_builder=environment_builder,
                    runner_builder=runner_builder,
                )
            )

    summary = {
        "sweep_parameter": sweep_parameter,
        "algorithms": list(algorithms),
        "runs": runs,
    }
    with (output_dir / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
    save_comparison_plots(summary=summary, output_dir=output_dir)
    return summary


def _build_runner_kwargs(algorithm_name: str, config: ExperimentConfig) -> dict[str, Any]:
    """Translate experiment config into algorithm-specific runner arguments."""
    if algorithm_name in {"capa", "greedy", "mra"}:
        return {"batch_size": config.batch_size}
    if algorithm_name == "impgta":
        return {"prediction_window_seconds": config.prediction_window_seconds}
    if algorithm_name == "rl-capa":
        return {
            "min_batch_size": int(config.extra.get("min_batch_size", 10)),
            "max_batch_size": int(config.extra.get("max_batch_size", 20)),
            "step_seconds": int(config.extra.get("step_seconds", 60)),
            "episodes": int(config.extra.get("episodes", 10)),
        }
    return {}


def _run_comparison_point(
    algorithms: Sequence[str],
    sweep_parameter: str,
    value: float,
    fixed_config: dict[str, Any],
    output_dir: Path,
    environment_builder: Callable[..., ChengduEnvironment] | None = None,
    runner_builder: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Run all algorithms for one sweep point against the same seeded Chengdu environment."""
    builder = environment_builder or ChengduEnvironment.build
    build_runner = runner_builder or build_algorithm_runner
    base_config = ExperimentConfig(
        data_dir=Path(fixed_config["data_dir"]),
        num_parcels=fixed_config.get("num_parcels", 100),
        local_couriers=fixed_config.get("local_couriers", 10),
        platforms=fixed_config.get("platforms", 2),
        couriers_per_platform=fixed_config.get("couriers_per_platform", 5),
        batch_size=fixed_config.get("batch_size", 300),
        prediction_window_seconds=fixed_config.get("prediction_window_seconds", 180),
        service_radius_km=fixed_config.get("service_radius_km"),
        courier_capacity=fixed_config.get("courier_capacity"),
        extra=dict(fixed_config.get("extra", {})),
    )
    point_config = apply_sweep_axis(base_config, sweep_parameter, value)
    environment = builder(**point_config.as_environment_kwargs())
    seed = build_environment_seed(environment)
    run_summary: dict[str, Any] = {sweep_parameter: value}
    for algorithm_name in algorithms:
        runner_kwargs = _build_runner_kwargs(algorithm_name=algorithm_name, config=point_config)
        runner = build_runner(algorithm_name, **runner_kwargs)
        algorithm_output_dir = output_dir / f"{sweep_parameter}_{value}" / algorithm_name
        summary = runner.run(
            environment=clone_environment_from_seed(seed),
            output_dir=algorithm_output_dir,
        )
        run_summary[algorithm_name] = summary
    return run_summary
