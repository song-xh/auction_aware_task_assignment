"""Run one Exp-1 parcel-count point from a shared canonical Chengdu seed."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.framework import ExperimentPointSpec, run_seeded_comparison_point
from experiments.seeding import derive_environment_from_seed


def run_exp1_point(
    seed_path: Path,
    num_parcels: int,
    output_dir: Path,
    algorithms: Sequence[str],
    batch_size: int,
    capa_runner_kwargs: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Run one parcel-count comparison point from a persisted canonical seed.

    Args:
        seed_path: Canonical seed bundle path.
        num_parcels: Parcel-count point.
        output_dir: Point output directory.
        algorithms: Algorithms executed at this point.
        batch_size: Shared batch size in seconds.
        capa_runner_kwargs: Optional CAPA-only runner overrides for managed retries.

    Returns:
        One normalized point summary.
    """

    runner_overrides_by_algorithm = {}
    if capa_runner_kwargs:
        runner_overrides_by_algorithm["capa"] = dict(capa_runner_kwargs)
    point_spec = ExperimentPointSpec(
        axis_name="num_parcels",
        axis_value=num_parcels,
        output_dir=output_dir,
        algorithms=algorithms,
        batch_size=batch_size,
        runner_overrides_by_algorithm=runner_overrides_by_algorithm,
    )
    return run_seeded_comparison_point(
        seed_path=seed_path,
        point_spec=point_spec,
        environment_deriver=lambda seed, value: derive_environment_from_seed(seed, num_parcels=value),
    )


def main() -> int:
    """Parse CLI arguments and run one Exp-1 point."""

    parser = argparse.ArgumentParser(description="Run one Exp-1 parcel-count point from a shared canonical seed.")
    parser.add_argument("--seed-path", required=True)
    parser.add_argument("--num-parcels", required=True, type=int)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--algorithms", nargs="+", required=True)
    parser.add_argument("--batch-size", type=int, default=30)
    parser.add_argument("--utility-balance-gamma", type=float, default=None)
    parser.add_argument("--threshold-omega", type=float, default=None)
    parser.add_argument("--local-payment-ratio-zeta", type=float, default=None)
    parser.add_argument("--local-sharing-rate-mu1", type=float, default=None)
    parser.add_argument("--cross-platform-sharing-rate-mu2", type=float, default=None)
    args = parser.parse_args()
    capa_runner_kwargs = {
        key: value
        for key, value in {
            "utility_balance_gamma": args.utility_balance_gamma,
            "threshold_omega": args.threshold_omega,
            "local_payment_ratio_zeta": args.local_payment_ratio_zeta,
            "local_sharing_rate_mu1": args.local_sharing_rate_mu1,
            "cross_platform_sharing_rate_mu2": args.cross_platform_sharing_rate_mu2,
        }.items()
        if value is not None
    }
    run_exp1_point(
        seed_path=Path(args.seed_path),
        num_parcels=args.num_parcels,
        output_dir=Path(args.output_dir),
        algorithms=args.algorithms,
        batch_size=args.batch_size,
        capa_runner_kwargs=capa_runner_kwargs or None,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
