"""Compatibility experiment helpers for Chengdu-backed CAPA runs."""

from __future__ import annotations

import argparse
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Sequence

from baselines.greedy import run_greedy_baseline_environment
from baselines.gta import (
    DEFAULT_IMPGTA_WINDOW_SECONDS,
    run_basegta_baseline_environment,
    run_impgta_baseline_environment,
)
from env.chengdu import LegacyChengduEnvironment, build_framework_chengdu_environment, run_time_stepped_chengdu_batches
from .metrics import compute_completion_rate, compute_total_revenue
from .models import BatchReport, CAPAConfig, CAPAResult, Parcel, RunMetrics


def load_chengdu_pickup_parcels(data_dir: Path, limit: int | None = None) -> list[Parcel]:
    """Load Chengdu pick-up parcels directly from the repository data files."""
    parcels: list[Parcel] = []
    for suffix in range(1, 5):
        file_path = data_dir / f"order_20161101_deal{suffix}"
        with file_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                cols = line.strip().split(",")
                if len(cols) < 8:
                    continue
                fare = float(cols[7])
                if fare == 0.0:
                    continue
                parcels.append(
                    Parcel(
                        parcel_id=str(cols[0]),
                        location=str(cols[3]),
                        arrival_time=int(float(cols[4])),
                        deadline=int(float(cols[5])),
                        weight=float(cols[6]),
                        fare=fare,
                    )
                )
    parcels.sort(key=lambda item: (item.arrival_time, item.deadline, item.parcel_id))
    if limit is not None:
        return parcels[:limit]
    return parcels


class ChengduGraphTravelModel:
    """Wrap the repository's Chengdu road graph as a CAPA travel model."""

    def __init__(self) -> None:
        """Import the Chengdu graph lazily so experiment helpers stay importable in tests."""
        from GraphUtils_ChengDu import NodeModel, VELOCITY, g, s

        self._NodeModel = NodeModel
        self._graph = g
        self._context = s
        self._speed = VELOCITY * 1000.0

    @lru_cache(maxsize=200_000)
    def distance(self, start: object, end: object) -> float:
        """Return shortest-path distance on the Chengdu road graph."""
        if start == end:
            return 0.0
        start_node = self._NodeModel()
        start_node.nodeId = str(start)
        end_node = self._NodeModel()
        end_node.nodeId = str(end)
        edges = self._graph.getShortPath(start_node, end_node, self._context)
        if not edges:
            raise ValueError(f"No Chengdu road path between {start!r} and {end!r}.")
        return float(sum(edge.length for edge in edges))

    def travel_time(self, start: object, end: object) -> float:
        """Return shortest-path travel time in seconds on the Chengdu graph."""
        if self._speed <= 0:
            raise ValueError("Graph travel speed must be positive.")
        return self.distance(start, end) / self._speed


def build_metric_series(batch_reports: Sequence[BatchReport], total_parcels: int) -> tuple[list[float], list[float], list[float]]:
    """Build batch-level TR, cumulative CR, and BPT series for plotting."""
    revenue_per_batch: list[float] = []
    completion_per_batch: list[float] = []
    bpt_per_batch: list[float] = []
    for report in batch_reports:
        assignments = [*report.local_assignments, *report.cross_assignments]
        revenue_per_batch.append(compute_total_revenue(assignments))
        completion_per_batch.append(compute_completion_rate([None] * report.delivered_parcel_count, total_parcels))
        bpt_per_batch.append(report.processing_time_seconds)
    return revenue_per_batch, completion_per_batch, bpt_per_batch


def save_experiment_plots(batch_reports: Sequence[BatchReport], metrics: RunMetrics, output_dir: Path) -> None:
    """Render TR, CR, and BPT plots for a Chengdu CAPA experiment."""
    import matplotlib.pyplot as plt

    output_dir.mkdir(parents=True, exist_ok=True)
    tr_values, cr_values, bpt_values = build_metric_series(batch_reports, sum(len(report.input_parcels) for report in batch_reports))
    batch_indices = list(range(1, len(batch_reports) + 1))

    plt.figure()
    plt.plot(batch_indices, tr_values, marker="o")
    plt.title(f"TR Over Batches (Total={metrics.total_revenue:.2f})")
    plt.xlabel("Batch")
    plt.ylabel("TR")
    plt.tight_layout()
    plt.savefig(output_dir / "tr_over_batches.png", dpi=150)
    plt.close()

    plt.figure()
    plt.plot(batch_indices, cr_values, marker="o")
    plt.title(f"CR Over Batches (Final={metrics.completion_rate:.4f})")
    plt.xlabel("Batch")
    plt.ylabel("CR")
    plt.tight_layout()
    plt.savefig(output_dir / "cr_over_batches.png", dpi=150)
    plt.close()

    plt.figure()
    plt.plot(batch_indices, bpt_values, marker="o")
    plt.title(f"BPT Over Batches (Total={metrics.batch_processing_time:.4f}s)")
    plt.xlabel("Batch")
    plt.ylabel("BPT (s)")
    plt.tight_layout()
    plt.savefig(output_dir / "bpt_over_batches.png", dpi=150)
    plt.close()


def build_default_chengdu_config(batch_size: int) -> CAPAConfig:
    """Construct the default Phase 4 Chengdu experiment configuration."""
    return CAPAConfig(
        batch_size=batch_size,
        utility_balance_gamma=0.5,
        threshold_omega=1.0,
        local_payment_ratio_zeta=0.2,
        local_sharing_rate_mu1=0.5,
        cross_platform_sharing_rate_mu2=0.4,
    )


def run_chengdu_experiment(
    data_dir: Path,
    num_parcels: int,
    local_courier_count: int,
    cooperating_platform_count: int,
    couriers_per_platform: int,
    batch_size: int,
    output_dir: Path,
    env_builder: Callable[..., LegacyChengduEnvironment | dict[str, Any]] | None = None,
) -> CAPAResult:
    """Run a full Chengdu-backed CAPA experiment and persist plots plus a summary JSON report."""
    builder = env_builder or build_framework_chengdu_environment
    built_environment = builder(
        data_dir=data_dir,
        num_parcels=num_parcels,
        local_courier_count=local_courier_count,
        cooperating_platform_count=cooperating_platform_count,
        couriers_per_platform=couriers_per_platform,
    )
    environment = built_environment if isinstance(built_environment, LegacyChengduEnvironment) else LegacyChengduEnvironment(**built_environment)
    config = build_default_chengdu_config(batch_size=batch_size)
    result = run_time_stepped_chengdu_batches(
        tasks=environment.tasks,
        local_couriers=environment.local_couriers,
        partner_couriers_by_platform=environment.partner_couriers_by_platform,
        station_set=environment.station_set,
        travel_model=environment.travel_model,
        config=config,
        batch_seconds=batch_size,
        step_seconds=60,
        platform_base_prices=environment.platform_base_prices,
        platform_sharing_rates=environment.platform_sharing_rates,
        platform_qualities=environment.platform_qualities,
        movement_callback=environment.movement_callback,
    )

    save_experiment_plots(result.batch_reports, result.metrics, output_dir)

    summary = {
        "num_parcels": len(environment.tasks),
        "local_courier_count": len(environment.local_couriers),
        "cooperating_platform_count": len(environment.partner_couriers_by_platform),
        "couriers_per_platform": couriers_per_platform,
        "batch_size": batch_size,
        "metrics": {
            "TR": result.metrics.total_revenue,
            "CR": result.metrics.completion_rate,
            "BPT": result.metrics.batch_processing_time,
            "delivered_parcels": result.metrics.delivered_parcel_count,
            "accepted_assignments": result.metrics.accepted_parcel_count,
        },
        "plots": {
            "TR": str(output_dir / "tr_over_batches.png"),
            "CR": str(output_dir / "cr_over_batches.png"),
            "BPT": str(output_dir / "bpt_over_batches.png"),
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)

    return result


def save_sweep_plots(summary: dict[str, Any], output_dir: Path) -> None:
    """Render aggregate TR, CR, and BPT plots for a one-dimensional Chengdu sweep."""
    import matplotlib.pyplot as plt

    runs = summary["runs"]
    parameter_name = summary["sweep_parameter"]
    x_values = [run[parameter_name] for run in runs]
    tr_values = [run["metrics"]["TR"] for run in runs]
    cr_values = [run["metrics"]["CR"] for run in runs]
    bpt_values = [run["metrics"]["BPT"] for run in runs]

    plt.figure()
    plt.plot(x_values, tr_values, marker="o")
    plt.xlabel(parameter_name)
    plt.ylabel("TR")
    plt.tight_layout()
    plt.savefig(output_dir / f"tr_vs_{parameter_name}.png", dpi=150)
    plt.close()

    plt.figure()
    plt.plot(x_values, cr_values, marker="o")
    plt.xlabel(parameter_name)
    plt.ylabel("CR")
    plt.tight_layout()
    plt.savefig(output_dir / f"cr_vs_{parameter_name}.png", dpi=150)
    plt.close()

    plt.figure()
    plt.plot(x_values, bpt_values, marker="o")
    plt.xlabel(parameter_name)
    plt.ylabel("BPT")
    plt.tight_layout()
    plt.savefig(output_dir / f"bpt_vs_{parameter_name}.png", dpi=150)
    plt.close()


def save_comparison_sweep_plots(summary: dict[str, Any], output_dir: Path) -> None:
    """Render aggregate comparison plots for CAPA versus Greedy over one sweep dimension."""
    import matplotlib.pyplot as plt

    runs = summary["runs"]
    parameter_name = summary["sweep_parameter"]
    x_values = [run[parameter_name] for run in runs]
    capa_tr = [run["capa"]["metrics"]["TR"] for run in runs]
    greedy_tr = [run["greedy"]["metrics"]["TR"] for run in runs]
    capa_cr = [run["capa"]["metrics"]["CR"] for run in runs]
    greedy_cr = [run["greedy"]["metrics"]["CR"] for run in runs]
    capa_bpt = [run["capa"]["metrics"]["BPT"] for run in runs]
    greedy_bpt = [run["greedy"]["metrics"]["BPT"] for run in runs]

    plt.figure()
    plt.plot(x_values, capa_tr, marker="o", label="CAPA")
    plt.plot(x_values, greedy_tr, marker="o", label="Greedy")
    plt.xlabel(parameter_name)
    plt.ylabel("TR")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_dir / f"tr_compare_vs_{parameter_name}.png", dpi=150)
    plt.close()

    plt.figure()
    plt.plot(x_values, capa_cr, marker="o", label="CAPA")
    plt.plot(x_values, greedy_cr, marker="o", label="Greedy")
    plt.xlabel(parameter_name)
    plt.ylabel("CR")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_dir / f"cr_compare_vs_{parameter_name}.png", dpi=150)
    plt.close()

    plt.figure()
    plt.plot(x_values, capa_bpt, marker="o", label="CAPA")
    plt.plot(x_values, greedy_bpt, marker="o", label="Greedy")
    plt.xlabel(parameter_name)
    plt.ylabel("BPT")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_dir / f"bpt_compare_vs_{parameter_name}.png", dpi=150)
    plt.close()


def run_chengdu_parameter_sweep(
    data_dir: Path,
    output_dir: Path,
    sweep_parameter: str,
    sweep_values: Sequence[int],
    fixed_config: dict[str, int],
    experiment_runner: Callable[..., CAPAResult] | None = None,
) -> dict[str, Any]:
    """Run a one-dimensional Chengdu parameter sweep and persist an aggregate summary."""
    runner = experiment_runner or run_chengdu_experiment
    runs: list[dict[str, Any]] = []
    output_dir.mkdir(parents=True, exist_ok=True)

    for value in sweep_values:
        experiment_config = dict(fixed_config)
        experiment_config[sweep_parameter] = value
        run_output_dir = output_dir / f"{sweep_parameter}_{value}"
        result = runner(
            data_dir=data_dir,
            output_dir=run_output_dir,
            **experiment_config,
        )
        runs.append(
            {
                sweep_parameter: value,
                "metrics": {
                    "TR": result.metrics.total_revenue,
                    "CR": result.metrics.completion_rate,
                    "BPT": result.metrics.batch_processing_time,
                    "delivered_parcels": result.metrics.delivered_parcel_count,
                    "accepted_assignments": result.metrics.accepted_parcel_count,
                },
                "output_dir": str(run_output_dir),
            }
        )

    summary = {
        "sweep_parameter": sweep_parameter,
        "fixed_config": fixed_config,
        "runs": runs,
    }
    with (output_dir / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
    save_sweep_plots(summary, output_dir)
    return summary


def run_chengdu_greedy_baseline(
    data_dir: Path,
    num_parcels: int,
    local_courier_count: int,
    batch_size: int,
    output_dir: Path,
    env_builder: Callable[..., LegacyChengduEnvironment | dict[str, Any]] | None = None,
    baseline_runner: Callable[..., dict[str, float]] | None = None,
) -> dict[str, Any]:
    """Run the official Chengdu Greedy baseline on the unified environment and persist a normalized summary."""
    builder = env_builder or build_framework_chengdu_environment
    built_environment = builder(
        data_dir=data_dir,
        num_parcels=num_parcels,
        local_courier_count=local_courier_count,
        cooperating_platform_count=0,
        couriers_per_platform=0,
    )
    environment = built_environment if isinstance(built_environment, LegacyChengduEnvironment) else LegacyChengduEnvironment(**built_environment)
    runner = baseline_runner or run_greedy_baseline_environment
    metrics = runner(
        environment=environment,
        batch_size=batch_size,
    )
    summary = {
        "algorithm": "greedy",
        "num_parcels": num_parcels,
        "local_courier_count": local_courier_count,
        "batch_size": batch_size,
        "metrics": metrics,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
    return summary


def run_chengdu_basegta_baseline(
    data_dir: Path,
    num_parcels: int,
    local_courier_count: int,
    cooperating_platform_count: int,
    couriers_per_platform: int,
    output_dir: Path,
    env_builder: Callable[..., LegacyChengduEnvironment | dict[str, Any]] | None = None,
    baseline_runner: Callable[..., dict[str, float]] | None = None,
) -> dict[str, Any]:
    """Run the BaseGTA baseline from [17] on the unified Chengdu environment."""
    builder = env_builder or build_framework_chengdu_environment
    built_environment = builder(
        data_dir=data_dir,
        num_parcels=num_parcels,
        local_courier_count=local_courier_count,
        cooperating_platform_count=cooperating_platform_count,
        couriers_per_platform=couriers_per_platform,
    )
    environment = built_environment if isinstance(built_environment, LegacyChengduEnvironment) else LegacyChengduEnvironment(**built_environment)
    runner = baseline_runner or run_basegta_baseline_environment
    metrics = runner(environment=environment)
    summary = {
        "algorithm": "basegta",
        "num_parcels": num_parcels,
        "local_courier_count": local_courier_count,
        "cooperating_platform_count": cooperating_platform_count,
        "couriers_per_platform": couriers_per_platform,
        "metrics": metrics,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
    return summary


def run_chengdu_impgta_baseline(
    data_dir: Path,
    num_parcels: int,
    local_courier_count: int,
    cooperating_platform_count: int,
    couriers_per_platform: int,
    output_dir: Path,
    prediction_window_seconds: int = DEFAULT_IMPGTA_WINDOW_SECONDS,
    env_builder: Callable[..., LegacyChengduEnvironment | dict[str, Any]] | None = None,
    baseline_runner: Callable[..., dict[str, float]] | None = None,
) -> dict[str, Any]:
    """Run the ImpGTA baseline from [17] on the unified Chengdu environment."""
    builder = env_builder or build_framework_chengdu_environment
    built_environment = builder(
        data_dir=data_dir,
        num_parcels=num_parcels,
        local_courier_count=local_courier_count,
        cooperating_platform_count=cooperating_platform_count,
        couriers_per_platform=couriers_per_platform,
    )
    environment = built_environment if isinstance(built_environment, LegacyChengduEnvironment) else LegacyChengduEnvironment(**built_environment)
    if baseline_runner is None:
        metrics = run_impgta_baseline_environment(
            environment=environment,
            prediction_window_seconds=prediction_window_seconds,
        )
    else:
        metrics = baseline_runner(environment=environment)
    summary = {
        "algorithm": "impgta",
        "num_parcels": num_parcels,
        "local_courier_count": local_courier_count,
        "cooperating_platform_count": cooperating_platform_count,
        "couriers_per_platform": couriers_per_platform,
        "prediction_window_seconds": prediction_window_seconds,
        "metrics": metrics,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
    return summary


def run_chengdu_comparison_sweep(
    data_dir: Path,
    output_dir: Path,
    sweep_parameter: str,
    sweep_values: Sequence[int],
    fixed_config: dict[str, int],
    capa_runner: Callable[..., Any] | None = None,
    baseline_runner: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Run CAPA and Greedy on the same parameter grid and persist a comparison summary."""
    capa_entry = capa_runner or (lambda **kwargs: run_chengdu_experiment(**kwargs))
    greedy_entry = baseline_runner or (lambda **kwargs: run_chengdu_greedy_baseline(**kwargs))
    runs: list[dict[str, Any]] = []
    output_dir.mkdir(parents=True, exist_ok=True)

    for value in sweep_values:
        experiment_config = dict(fixed_config)
        experiment_config[sweep_parameter] = value
        capa_output_dir = output_dir / f"{sweep_parameter}_{value}" / "capa"
        greedy_output_dir = output_dir / f"{sweep_parameter}_{value}" / "greedy"
        capa_result = capa_entry(
            data_dir=data_dir,
            output_dir=capa_output_dir,
            **experiment_config,
        )
        if isinstance(capa_result, CAPAResult):
            capa_summary = {
                "algorithm": "capa",
                "metrics": {
                    "TR": capa_result.metrics.total_revenue,
                    "CR": capa_result.metrics.completion_rate,
                    "BPT": capa_result.metrics.batch_processing_time,
                    "delivered_parcels": capa_result.metrics.delivered_parcel_count,
                    "accepted_assignments": capa_result.metrics.accepted_parcel_count,
                },
            }
        else:
            capa_summary = capa_result

        greedy_result = greedy_entry(
            data_dir=data_dir,
            output_dir=greedy_output_dir,
            num_parcels=experiment_config["num_parcels"],
            local_courier_count=experiment_config["local_courier_count"],
            batch_size=experiment_config["batch_size"],
        )
        runs.append(
            {
                sweep_parameter: value,
                "capa": capa_summary,
                "greedy": greedy_result,
            }
        )

    summary = {
        "sweep_parameter": sweep_parameter,
        "fixed_config": fixed_config,
        "runs": runs,
    }
    with (output_dir / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
    save_comparison_sweep_plots(summary, output_dir)
    return summary


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for the Chengdu experiment entrypoint."""
    parser = argparse.ArgumentParser(description="Run the Phase 4 CAPA experiment on the Chengdu dataset.")
    parser.add_argument("--data-dir", default="Data", help="Path to the Chengdu data directory.")
    parser.add_argument("--num-parcels", type=int, default=100, help="Number of pick-up parcels to evaluate.")
    parser.add_argument("--local-couriers", type=int, default=10, help="Number of local couriers.")
    parser.add_argument("--platforms", type=int, default=2, help="Number of cooperating platforms.")
    parser.add_argument("--couriers-per-platform", type=int, default=5, help="Number of couriers in each cooperating platform.")
    parser.add_argument("--batch-size", type=int, default=300, help="Batch size for Algorithm 1.")
    parser.add_argument("--output-dir", default="outputs/plots/chengdu_capa", help="Directory for plots and summary files.")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint for the Chengdu CAPA experiment."""
    args = parse_args(argv)
    result = run_chengdu_experiment(
        data_dir=Path(args.data_dir),
        num_parcels=args.num_parcels,
        local_courier_count=args.local_couriers,
        cooperating_platform_count=args.platforms,
        couriers_per_platform=args.couriers_per_platform,
        batch_size=args.batch_size,
        output_dir=Path(args.output_dir),
    )
    print(f"TR={result.metrics.total_revenue:.4f}")
    print(f"CR={result.metrics.completion_rate:.6f}")
    print(f"BPT={result.metrics.batch_processing_time:.6f}s")
    print(f"plots={Path(args.output_dir).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
