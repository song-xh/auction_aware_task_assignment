"""Unified root CLI for Chengdu environment experiments."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Sequence

from algorithms.registry import build_algorithm_runner, get_algorithm_names
from env.chengdu import ChengduEnvironment
from experiments.compare import run_comparison_sweep
from experiments.sweep import run_parameter_sweep
from experiments.suites import run_experiment_suite


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for single runs, sweeps, and shared-environment comparisons."""
    normalized_argv = list(sys.argv[1:] if argv is None else argv)
    if normalized_argv and normalized_argv[0].startswith("-"):
        normalized_argv = ["run", *normalized_argv]

    parser = argparse.ArgumentParser(description="Run Chengdu experiments through the unified environment and algorithm registry.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run one algorithm on one Chengdu configuration.")
    _add_common_environment_arguments(run_parser)
    run_parser.add_argument("--algorithm", choices=get_algorithm_names(), required=True, help="Algorithm to execute.")

    sweep_parser = subparsers.add_parser("sweep", help="Run a one-dimensional sweep for a single algorithm.")
    _add_common_environment_arguments(sweep_parser)
    sweep_parser.add_argument("--algorithm", choices=get_algorithm_names(), required=True, help="Algorithm to execute.")
    sweep_parser.add_argument("--axis", required=True, help="Sweep axis, for example `num_parcels` or `batch_size`.")
    sweep_parser.add_argument("--values", type=float, nargs="+", required=True, help="Ordered sweep values for the selected axis.")
    sweep_parser.add_argument("--max-workers", type=int, default=None, help="Optional process count for parallel sweep-point execution.")

    compare_parser = subparsers.add_parser("compare", help="Run a shared-environment comparison across algorithms.")
    _add_common_environment_arguments(compare_parser)
    compare_parser.add_argument("--algorithms", choices=get_algorithm_names(), nargs="+", required=True, help="Algorithms to compare.")
    compare_parser.add_argument("--axis", required=True, help="Sweep axis, for example `num_parcels` or `batch_size`.")
    compare_parser.add_argument("--values", type=float, nargs="+", required=True, help="Ordered sweep values for the selected axis.")
    compare_parser.add_argument("--max-workers", type=int, default=None, help="Optional process count for parallel sweep-point execution.")

    suite_parser = subparsers.add_parser("suite", help="Run a predefined paper-style suite of sweeps.")
    _add_common_environment_arguments(suite_parser)
    suite_parser.add_argument("--suite", required=True, help="Predefined suite name, for example `chengdu-paper`.")
    suite_parser.add_argument("--preset", default="formal", help="Preset grid for the selected suite.")
    suite_parser.add_argument("--algorithms", choices=get_algorithm_names(), nargs="+", required=True, help="Algorithms to compare in the suite.")
    suite_parser.add_argument("--max-workers", type=int, default=None, help="Optional process count for parallel sweep-point execution.")

    return parser.parse_args(normalized_argv)


def _add_common_environment_arguments(parser: argparse.ArgumentParser) -> None:
    """Register the common Chengdu environment and algorithm arguments on one parser."""
    parser.add_argument("--data-dir", default="Data", help="Path to the Chengdu data directory.")
    parser.add_argument("--num-parcels", type=int, default=100, help="Number of parcels to include in the run.")
    parser.add_argument("--local-couriers", type=int, default=10, help="Number of local couriers.")
    parser.add_argument("--platforms", type=int, default=2, help="Number of cooperating platforms.")
    parser.add_argument("--couriers-per-platform", type=int, default=5, help="Number of couriers per cooperating platform.")
    parser.add_argument("--courier-capacity", type=float, default=None, help="Optional courier capacity override for all seeded couriers.")
    parser.add_argument("--service-radius-km", type=float, default=None, help="Optional courier service radius in kilometers.")
    parser.add_argument("--batch-size", type=int, default=300, help="Batch size in seconds for algorithms that use batching.")
    parser.add_argument("--min-batch-size", type=int, default=10, help="Lower bound of the RL-CAPA batch-size action space.")
    parser.add_argument("--max-batch-size", type=int, default=20, help="Upper bound of the RL-CAPA batch-size action space.")
    parser.add_argument("--step-seconds", type=int, default=60, help="Simulation step size in seconds for RL-CAPA.")
    parser.add_argument("--episodes", type=int, default=10, help="Training episodes used by RL-CAPA before evaluation.")
    parser.add_argument(
        "--prediction-window-seconds",
        type=int,
        default=180,
        help="Future observation window in seconds for ImpGTA.",
    )
    parser.add_argument("--output-dir", default="outputs/plots/chengdu_run", help="Directory for summary files and plots.")


def build_algorithm_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    """Translate parsed CLI arguments into algorithm-specific runner configuration."""
    if args.algorithm in {"capa", "greedy", "mra"}:
        return {"batch_size": args.batch_size}
    if args.algorithm == "impgta":
        return {"prediction_window_seconds": args.prediction_window_seconds}
    if args.algorithm == "rl-capa":
        return {
            "min_batch_size": args.min_batch_size,
            "max_batch_size": args.max_batch_size,
            "step_seconds": args.step_seconds,
            "episodes": args.episodes,
        }
    return {}


def main(argv: Sequence[str] | None = None) -> int:
    """Dispatch single runs, sweeps, or comparisons through the unified CLI."""
    args = parse_args(argv)
    if args.command == "run":
        return _run_single_experiment(args)
    if args.command == "sweep":
        return _run_sweep(args)
    if args.command == "compare":
        return _run_compare(args)
    if args.command == "suite":
        return _run_suite(args)
    raise ValueError(f"Unsupported command: {args.command}")


def _run_single_experiment(args: argparse.Namespace) -> int:
    """Build the Chengdu environment once and run the selected algorithm."""
    environment = ChengduEnvironment.build(
        data_dir=Path(args.data_dir),
        num_parcels=args.num_parcels,
        local_courier_count=args.local_couriers,
        cooperating_platform_count=args.platforms,
        couriers_per_platform=args.couriers_per_platform,
        service_radius_km=args.service_radius_km,
        courier_capacity=args.courier_capacity,
    )
    runner = build_algorithm_runner(args.algorithm, **build_algorithm_kwargs(args))
    try:
        summary = runner.run(
            environment=environment,
            output_dir=Path(args.output_dir),
        )
    except NotImplementedError as error:
        print(str(error), file=sys.stderr)
        return 1
    print(f"algorithm={summary['algorithm']}")
    for metric_name, value in summary.get("metrics", {}).items():
        print(f"{metric_name}={value}")
    print(f"output_dir={Path(args.output_dir).resolve()}")
    return 0


def _run_sweep(args: argparse.Namespace) -> int:
    """Run a one-dimensional sweep for a single algorithm and print the summary location."""
    summary = run_parameter_sweep(
        algorithm=args.algorithm,
        output_dir=Path(args.output_dir),
        sweep_parameter=args.axis,
        sweep_values=args.values,
        fixed_config=_build_fixed_config(args),
        max_workers=args.max_workers,
    )
    print(f"algorithm={summary.get('algorithm', args.algorithm)}")
    print(f"sweep_parameter={summary.get('sweep_parameter', args.axis)}")
    print(f"output_dir={Path(args.output_dir).resolve()}")
    return 0


def _run_compare(args: argparse.Namespace) -> int:
    """Run a shared-environment comparison sweep across multiple algorithms."""
    summary = run_comparison_sweep(
        algorithms=args.algorithms,
        output_dir=Path(args.output_dir),
        sweep_parameter=args.axis,
        sweep_values=args.values,
        fixed_config=_build_fixed_config(args),
        max_workers=args.max_workers,
    )
    print(f"algorithms={','.join(summary.get('algorithms', args.algorithms))}")
    print(f"sweep_parameter={summary.get('sweep_parameter', args.axis)}")
    print(f"output_dir={Path(args.output_dir).resolve()}")
    return 0


def _run_suite(args: argparse.Namespace) -> int:
    """Run one predefined experiment suite and print the summary location."""
    summary = run_experiment_suite(
        suite_name=args.suite,
        preset_name=args.preset,
        algorithms=args.algorithms,
        output_dir=Path(args.output_dir),
        fixed_config=_build_fixed_config(args),
        max_workers=args.max_workers,
    )
    print(f"suite={summary.get('suite', args.suite)}")
    print(f"preset={summary.get('preset', args.preset)}")
    print(f"algorithms={','.join(summary.get('algorithms', args.algorithms))}")
    print(f"output_dir={Path(args.output_dir).resolve()}")
    return 0


def _build_fixed_config(args: argparse.Namespace) -> dict[str, Any]:
    """Extract the shared fixed configuration from parsed CLI arguments."""
    return {
        "data_dir": Path(args.data_dir),
        "num_parcels": args.num_parcels,
        "local_couriers": args.local_couriers,
        "platforms": args.platforms,
        "couriers_per_platform": args.couriers_per_platform,
        "courier_capacity": args.courier_capacity,
        "service_radius_km": args.service_radius_km,
        "batch_size": args.batch_size,
        "prediction_window_seconds": args.prediction_window_seconds,
    }


if __name__ == "__main__":
    raise SystemExit(main())
