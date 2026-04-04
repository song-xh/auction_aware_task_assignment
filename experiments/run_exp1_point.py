"""Run one Exp-1 parcel-count point from a shared canonical Chengdu seed."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from algorithms.registry import build_algorithm_runner
from experiments.plotting import save_comparison_plots
from experiments.seeding import build_environment_seed, clone_environment_from_seed, derive_environment_from_seed, load_environment_seed


def run_exp1_point(
    seed_path: Path,
    num_parcels: int,
    output_dir: Path,
    algorithms: Sequence[str],
    batch_size: int,
) -> dict[str, Any]:
    """Run one parcel-count comparison point from a persisted canonical seed.

    Args:
        seed_path: Canonical seed bundle path.
        num_parcels: Parcel-count point.
        output_dir: Point output directory.
        algorithms: Algorithms executed at this point.
        batch_size: Shared batch size in seconds.

    Returns:
        One normalized point summary.
    """

    seed = load_environment_seed(seed_path)
    point_environment = derive_environment_from_seed(seed, num_parcels=num_parcels)
    point_seed = build_environment_seed(point_environment)
    output_dir.mkdir(parents=True, exist_ok=True)
    point_summary: dict[str, Any] = {"num_parcels": num_parcels}
    for algorithm in algorithms:
        runner_kwargs: dict[str, Any] = {}
        if algorithm in {"capa", "greedy", "mra"}:
            runner_kwargs["batch_size"] = batch_size
        elif algorithm == "impgta":
            runner_kwargs["prediction_window_seconds"] = 180
        runner = build_algorithm_runner(algorithm, **runner_kwargs)
        point_summary[algorithm] = runner.run(
            environment=clone_environment_from_seed(point_seed),
            output_dir=output_dir / algorithm,
        )
    with (output_dir / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(point_summary, handle, indent=2)
    return point_summary


def main() -> int:
    """Parse CLI arguments and run one Exp-1 point."""

    parser = argparse.ArgumentParser(description="Run one Exp-1 parcel-count point from a shared canonical seed.")
    parser.add_argument("--seed-path", required=True)
    parser.add_argument("--num-parcels", required=True, type=int)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--algorithms", nargs="+", required=True)
    parser.add_argument("--batch-size", type=int, default=30)
    args = parser.parse_args()
    run_exp1_point(
        seed_path=Path(args.seed_path),
        num_parcels=args.num_parcels,
        output_dir=Path(args.output_dir),
        algorithms=args.algorithms,
        batch_size=args.batch_size,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
