"""Single-algorithm sweep orchestration for the unified Chengdu runner."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Sequence

from algorithms.registry import build_algorithm_runner
from env.chengdu import ChengduEnvironment

from .config import ExperimentConfig, apply_sweep_axis
from .plotting import save_single_algorithm_plots


def run_parameter_sweep(
    algorithm: str,
    output_dir: Path,
    sweep_parameter: str,
    sweep_values: Sequence[int],
    fixed_config: dict[str, Any],
    environment_builder: Callable[..., ChengduEnvironment] | None = None,
    runner_builder: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Run a one-dimensional sweep for one algorithm and persist a normalized summary.

    Args:
        algorithm: Algorithm name executed at every sweep point.
        output_dir: Directory that receives the aggregate summary.
        sweep_parameter: Parameter varied across the sweep.
        sweep_values: Ordered values explored on the chosen axis.
        fixed_config: Base configuration shared across the sweep.
        environment_builder: Optional injected environment builder for tests.
        runner_builder: Optional injected algorithm runner builder for tests.

    Returns:
        A normalized sweep summary keyed by run.
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

    for value in sweep_values:
        point_config = apply_sweep_axis(base_config, sweep_parameter, value)
        environment = builder(**point_config.as_environment_kwargs())
        runner_kwargs = _build_runner_kwargs(algorithm_name=algorithm, config=point_config)
        runner = build_runner(algorithm, **runner_kwargs)
        run_output_dir = output_dir / f"{sweep_parameter}_{value}" / algorithm
        summary = runner.run(environment=environment, output_dir=run_output_dir)
        runs.append(
            {
                sweep_parameter: value,
                algorithm: summary,
            }
        )

    summary = {
        "sweep_parameter": sweep_parameter,
        "algorithm": algorithm,
        "runs": runs,
    }
    with (output_dir / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
    save_single_algorithm_plots(summary=summary, output_dir=output_dir)
    return summary


def _build_runner_kwargs(algorithm_name: str, config: ExperimentConfig) -> dict[str, Any]:
    """Translate experiment config into algorithm-specific runner arguments."""
    if algorithm_name in {"capa", "greedy", "mra"}:
        return {"batch_size": config.batch_size}
    if algorithm_name == "impgta":
        return {"prediction_window_seconds": config.prediction_window_seconds}
    return {}
