"""Launch Exp-1 as four independent parcel-count processes from one shared canonical seed."""

from __future__ import annotations

import argparse
import json
from io import TextIOWrapper
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from env.chengdu import ChengduEnvironment
from experiments.paper_chengdu import DEFAULT_CHENGDU_PAPER_FIXED_CONFIG
from experiments.paper_config import DEFAULT_CHENGDU_PAPER_ALGORITHMS, PAPER_SUITE_PRESETS
from experiments.plotting import save_comparison_plots
from experiments.seeding import build_environment_seed, save_environment_seed


def run_exp1_split(
    tmp_root: Path,
    output_dir: Path,
    algorithms: Sequence[str] = DEFAULT_CHENGDU_PAPER_ALGORITHMS,
    parcel_values: Sequence[int] = tuple(int(value) for value in PAPER_SUITE_PRESETS["chengdu-paper"]["formal"]["num_parcels"]),
    fixed_config_overrides: dict[str, Any] | None = None,
    batch_size: int = 30,
    poll_seconds: int = 30,
    seed_path: Path | None = None,
    capa_runner_kwargs: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Launch one process per Exp-1 parcel-count point from a shared canonical seed.

    Args:
        tmp_root: Temporary root for canonical seed and per-point outputs.
        output_dir: Final aggregate output directory.
        algorithms: Algorithms included in every point process.
        parcel_values: Parcel-count points.
        fixed_config_overrides: Optional configuration overrides.
        batch_size: Shared batch size in seconds.
        poll_seconds: Launcher polling interval in seconds.
        seed_path: Optional existing canonical seed bundle reused across rounds.
        capa_runner_kwargs: Optional CAPA-only override set forwarded to point processes.

    Returns:
        Aggregate Exp-1 comparison summary.
    """

    tmp_root.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    fixed_config = dict(DEFAULT_CHENGDU_PAPER_FIXED_CONFIG)
    if fixed_config_overrides:
        fixed_config.update(fixed_config_overrides)
    if seed_path is None:
        max_num_parcels = max(int(value) for value in parcel_values)
        canonical_environment = ChengduEnvironment.build(
            data_dir=Path(fixed_config["data_dir"]),
            num_parcels=max_num_parcels,
            local_courier_count=int(fixed_config["local_couriers"]),
            cooperating_platform_count=int(fixed_config["platforms"]),
            couriers_per_platform=int(fixed_config["couriers_per_platform"]),
            service_radius_km=fixed_config["service_radius_km"],
            courier_capacity=fixed_config["courier_capacity"],
        )
        seed_path = tmp_root / "canonical_seed.pkl"
        save_environment_seed(build_environment_seed(canonical_environment), seed_path)

    processes: dict[int, subprocess.Popen[str]] = {}
    log_handles: list[TextIOWrapper] = []
    point_output_dirs: dict[int, Path] = {}
    try:
        for value in parcel_values:
            point_output_dir = tmp_root / f"point_{int(value)}"
            point_output_dirs[int(value)] = point_output_dir
            point_output_dir.mkdir(parents=True, exist_ok=True)
            stdout_handle = (point_output_dir / "stdout.log").open("w", encoding="utf-8")
            stderr_handle = (point_output_dir / "stderr.log").open("w", encoding="utf-8")
            log_handles.extend([stdout_handle, stderr_handle])
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-u",
                    str(Path(__file__).with_name("run_exp1_point.py")),
                    "--seed-path",
                    str(seed_path),
                    "--num-parcels",
                    str(int(value)),
                    "--output-dir",
                    str(point_output_dir),
                    "--algorithms",
                    *list(algorithms),
                    "--batch-size",
                    str(batch_size),
                    *build_capa_cli_args(capa_runner_kwargs or {}),
                ],
                cwd=Path(__file__).resolve().parents[1],
                stdout=stdout_handle,
                stderr=stderr_handle,
                text=True,
            )
            processes[int(value)] = process

        status_path = tmp_root / "split_status.json"
        while processes:
            point_status = {}
            finished: list[int] = []
            for value, process in processes.items():
                return_code = process.poll()
                point_status[str(value)] = {
                    "pid": process.pid,
                    "returncode": return_code,
                    "output_dir": str(point_output_dirs[value]),
                }
                if return_code is not None:
                    finished.append(value)
            with status_path.open("w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "state": "running" if processes else "finished",
                        "points": point_status,
                        "updated_at": time.time(),
                    },
                    handle,
                    indent=2,
                )
            if not finished:
                time.sleep(poll_seconds)
                continue
            for value in finished:
                process = processes.pop(value)
                if process.returncode != 0:
                    raise RuntimeError(
                        f"Exp-1 point {value} failed. See {point_output_dirs[value] / 'stderr.log'}"
                    )
    finally:
        for handle in log_handles:
            handle.close()

    runs = []
    for value in sorted(int(item) for item in parcel_values):
        with (point_output_dirs[value] / "summary.json").open("r", encoding="utf-8") as handle:
            runs.append(json.load(handle))
    summary = {
        "sweep_parameter": "num_parcels",
        "algorithms": list(algorithms),
        "runs": runs,
    }
    with (output_dir / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
    save_comparison_plots(summary=summary, output_dir=output_dir)
    with (output_dir / "split_manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(
            {
                "seed_path": str(seed_path),
                "tmp_root": str(tmp_root),
                "algorithms": list(algorithms),
                "parcel_values": [int(value) for value in parcel_values],
                "batch_size": batch_size,
                "summary": str(output_dir / "summary.json"),
            },
            handle,
            indent=2,
        )
    return summary


def main() -> int:
    """Parse CLI arguments and launch the split-process Exp-1 suite."""

    parser = argparse.ArgumentParser(description="Launch Exp-1 as one process per parcel-count point.")
    parser.add_argument("--tmp-root", default="/tmp/exp1_split")
    parser.add_argument("--output-dir", default="outputs/plots/exp1_split")
    parser.add_argument("--algorithms", nargs="+", default=list(DEFAULT_CHENGDU_PAPER_ALGORITHMS))
    parser.add_argument("--batch-size", type=int, default=30)
    parser.add_argument("--poll-seconds", type=int, default=30)
    parser.add_argument("--seed-path", default=None)
    parser.add_argument("--data-dir", default="Data")
    parser.add_argument("--local-couriers", type=int, default=DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["local_couriers"])
    parser.add_argument("--platforms", type=int, default=DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["platforms"])
    parser.add_argument("--couriers-per-platform", type=int, default=DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["couriers_per_platform"])
    parser.add_argument("--courier-capacity", type=float, default=DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["courier_capacity"])
    parser.add_argument("--service-radius-km", type=float, default=DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["service_radius_km"])
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
    run_exp1_split(
        tmp_root=Path(args.tmp_root),
        output_dir=Path(args.output_dir),
        algorithms=args.algorithms,
        fixed_config_overrides={
            "data_dir": Path(args.data_dir),
            "local_couriers": args.local_couriers,
            "platforms": args.platforms,
            "couriers_per_platform": args.couriers_per_platform,
            "courier_capacity": args.courier_capacity,
            "service_radius_km": args.service_radius_km,
        },
        batch_size=args.batch_size,
        poll_seconds=args.poll_seconds,
        seed_path=Path(args.seed_path) if args.seed_path is not None else None,
        capa_runner_kwargs=capa_runner_kwargs or None,
    )
    return 0


def build_capa_cli_args(capa_runner_kwargs: dict[str, float]) -> list[str]:
    """Translate CAPA override kwargs into `run_exp1_point.py` CLI flags.

    Args:
        capa_runner_kwargs: CAPA-only override mapping.

    Returns:
        Flat CLI argument list.
    """

    flag_mapping = {
        "utility_balance_gamma": "--utility-balance-gamma",
        "threshold_omega": "--threshold-omega",
        "local_payment_ratio_zeta": "--local-payment-ratio-zeta",
        "local_sharing_rate_mu1": "--local-sharing-rate-mu1",
        "cross_platform_sharing_rate_mu2": "--cross-platform-sharing-rate-mu2",
    }
    args: list[str] = []
    for key, flag in flag_mapping.items():
        if key in capa_runner_kwargs:
            args.extend([flag, str(capa_runner_kwargs[key])])
    return args


if __name__ == "__main__":
    raise SystemExit(main())
