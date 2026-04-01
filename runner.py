"""Unified root CLI for Chengdu environment experiments."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Sequence

from algorithms.registry import build_algorithm_runner, get_algorithm_names
from env.chengdu import ChengduEnvironment


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for the unified Chengdu experiment runner."""
    parser = argparse.ArgumentParser(description="Run Chengdu experiments through the unified environment and algorithm registry.")
    parser.add_argument("--algorithm", choices=get_algorithm_names(), required=True, help="Algorithm to execute.")
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
    return parser.parse_args(argv)


def build_algorithm_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    """Translate parsed CLI arguments into algorithm-specific runner configuration."""
    if args.algorithm in {"capa", "greedy"}:
        return {"batch_size": args.batch_size}
    if args.algorithm == "impgta":
        return {"prediction_window_seconds": args.prediction_window_seconds}
    return {}


def main(argv: Sequence[str] | None = None) -> int:
    """Build the Chengdu environment once and run the selected algorithm."""
    args = parse_args(argv)
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


if __name__ == "__main__":
    raise SystemExit(main())
