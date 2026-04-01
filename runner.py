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


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for single runs, sweeps, and shared-environment comparisons."""
    normalized_argv = list(argv or [])
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
    sweep_parser.add_argument("--values", type=int, nargs="+", required=True, help="Ordered sweep values for the selected axis.")

    compare_parser = subparsers.add_parser("compare", help="Run a shared-environment comparison across algorithms.")
    _add_common_environment_arguments(compare_parser)
    compare_parser.add_argument("--algorithms", choices=get_algorithm_names(), nargs="+", required=True, help="Algorithms to compare.")
    compare_parser.add_argument("--axis", required=True, help="Sweep axis, for example `num_parcels` or `batch_size`.")
    compare_parser.add_argument("--values", type=int, nargs="+", required=True, help="Ordered sweep values for the selected axis.")

    return parser.parse_args(normalized_argv)


def _add_common_environment_arguments(parser: argparse.ArgumentParser) -> None:
    """Register the common Chengdu environment and algorithm arguments on one parser."""
    parser.add_argument("--data-dir", default="Data", help="Path to the Chengdu data directory.")
    parser.add_argument("--num-parcels", type=int, default=100, help="Number of parcels to include in the run.")
    parser.add_argument("--local-couriers", type=int, default=10, help="Number of local couriers.")
    parser.add_argument("--platforms", type=int, default=2, help="Number of cooperating platforms.")
    parser.add_argument("--couriers-per-platform", type=int, default=5, help="Number of couriers per cooperating platform.")
    parser.add_argument("--batch-size", type=int, default=300, help="Batch size in seconds for algorithms that use batching.")
    parser.add_argument(
        "--prediction-window-seconds",
        type=int,
        default=180,
        help="Future observation window in seconds for ImpGTA.",
    )
    parser.add_argument("--output-dir", default="outputs/plots/chengdu_run", help="Directory for summary files and plots.")


def build_algorithm_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    """Translate parsed CLI arguments into algorithm-specific runner configuration."""
    if args.algorithm in {"capa", "greedy"}:
        return {"batch_size": args.batch_size}
    if args.algorithm == "impgta":
        return {"prediction_window_seconds": args.prediction_window_seconds}
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
    raise ValueError(f"Unsupported command: {args.command}")


def _run_single_experiment(args: argparse.Namespace) -> int:
    """Build the Chengdu environment once and run the selected algorithm."""
    environment = ChengduEnvironment.build(
        data_dir=Path(args.data_dir),
        num_parcels=args.num_parcels,
        local_courier_count=args.local_couriers,
        cooperating_platform_count=args.platforms,
        couriers_per_platform=args.couriers_per_platform,
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
    )
    print(f"algorithms={','.join(summary.get('algorithms', args.algorithms))}")
    print(f"sweep_parameter={summary.get('sweep_parameter', args.axis)}")
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
        "batch_size": args.batch_size,
        "prediction_window_seconds": args.prediction_window_seconds,
    }


if __name__ == "__main__":
    raise SystemExit(main())
