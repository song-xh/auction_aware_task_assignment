"""Long-interval supervisor for split-process Exp-1 runs."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.monitor_exp1_split import collect_split_progress
from experiments.paper_chengdu import DEFAULT_CHENGDU_PAPER_FIXED_CONFIG
from experiments.paper_config import DEFAULT_CHENGDU_PAPER_ALGORITHMS
from experiments.run_exp1_managed import DEFAULT_EXP1_ROUNDS, analyze_exp1_summary


def supervise_exp1_split(
    current_tmp_root: Path,
    current_output_dir: Path,
    snapshot_path: Path,
    log_path: Path,
    analysis_path: Path,
    data_dir: Path,
    algorithms: Sequence[str] = DEFAULT_CHENGDU_PAPER_ALGORITHMS,
    batch_size: int = 30,
    local_couriers: int = int(DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["local_couriers"]),
    platforms: int = int(DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["platforms"]),
    couriers_per_platform: int = int(DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["couriers_per_platform"]),
    courier_capacity: float = float(DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["courier_capacity"]),
    service_radius_km: float = float(DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["service_radius_km"]),
    poll_seconds: int = 1800,
    success_tr_ratio: float = 0.9,
    success_cr_gap: float = 0.02,
    max_rounds: int = len(DEFAULT_EXP1_ROUNDS),
    next_tmp_root_base: Path = Path("/tmp/exp1_split_managed"),
    next_output_dir_base: Path = Path("outputs/plots/exp1_split_managed"),
    stop_after_launch: bool = False,
) -> dict[str, Any]:
    """Monitor one split Exp-1 run, analyze results, and launch later CAPA rounds when needed.

    Args:
        current_tmp_root: Temp root for the current split round.
        current_output_dir: Aggregate output directory for the current split round.
        snapshot_path: Rolling supervisor JSON snapshot path.
        log_path: Append-only supervisor log path.
        analysis_path: Latest round analysis JSON path.
        data_dir: Chengdu data directory.
        algorithms: Algorithms participating in the comparison.
        batch_size: Shared batch size in seconds.
        local_couriers: Local courier count.
        platforms: Cooperating platform count.
        couriers_per_platform: Couriers per cooperating platform.
        courier_capacity: Courier capacity.
        service_radius_km: Service radius in kilometers.
        poll_seconds: Long-interval polling cadence.
        success_tr_ratio: Minimum accepted CAPA TR ratio versus the strongest baseline.
        success_cr_gap: Maximum accepted CAPA CR gap versus the strongest baseline.
        max_rounds: Maximum CAPA rounds allowed, in the order defined by `DEFAULT_EXP1_ROUNDS`.
        next_tmp_root_base: Base temp root used for newly launched rounds.
        next_output_dir_base: Base output directory used for newly launched rounds.
        stop_after_launch: Testing hook that returns immediately after a retry round is launched.

    Returns:
        Manifest describing the latest analyzed round and any launched next round.
    """

    current_round_index = 1
    current_seed_path = current_tmp_root / "canonical_seed.pkl"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    analysis_path.parent.mkdir(parents=True, exist_ok=True)

    while True:
        snapshot = collect_split_progress(current_tmp_root)
        snapshot_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
        _append_supervisor_log_line(log_path=log_path, snapshot=snapshot, round_index=current_round_index)
        if snapshot["state"] != "finished":
            time.sleep(poll_seconds)
            continue

        summary = json.loads((current_output_dir / "summary.json").read_text(encoding="utf-8"))
        round_spec = DEFAULT_EXP1_ROUNDS[current_round_index - 1]
        analysis = analyze_exp1_summary(
            summary=summary,
            algorithms=algorithms,
            round_spec=round_spec,
            success_tr_ratio=success_tr_ratio,
            success_cr_gap=success_cr_gap,
        )
        analysis_path.write_text(json.dumps(analysis, indent=2), encoding="utf-8")
        if analysis["accepted"] or current_round_index >= min(max_rounds, len(DEFAULT_EXP1_ROUNDS)):
            manifest = {
                "accepted": analysis["accepted"],
                "round_index": current_round_index,
                "round_name": round_spec.name,
                "recommendation": analysis["recommendation"],
                "analysis_path": str(analysis_path),
                "current_tmp_root": str(current_tmp_root),
                "current_output_dir": str(current_output_dir),
            }
            return manifest

        next_round_index = _select_next_round_index(current_round_index=current_round_index, recommendation=analysis["recommendation"])
        next_round_spec = DEFAULT_EXP1_ROUNDS[next_round_index - 1]
        next_tmp_root = next_tmp_root_base / f"round_{next_round_index:02d}_{next_round_spec.name}"
        next_output_dir = next_output_dir_base / f"round_{next_round_index:02d}_{next_round_spec.name}"
        process = _launch_next_round(
            seed_path=current_seed_path,
            tmp_root=next_tmp_root,
            output_dir=next_output_dir,
            data_dir=data_dir,
            algorithms=algorithms,
            batch_size=batch_size,
            local_couriers=local_couriers,
            platforms=platforms,
            couriers_per_platform=couriers_per_platform,
            courier_capacity=courier_capacity,
            service_radius_km=service_radius_km,
            capa_runner_kwargs=next_round_spec.capa_runner_kwargs,
        )
        launch_manifest = {
            "accepted": False,
            "round_index": current_round_index,
            "round_name": round_spec.name,
            "recommendation": analysis["recommendation"],
            "analysis_path": str(analysis_path),
            "launched_next_round": {
                "round_index": next_round_index,
                "round_name": next_round_spec.name,
                "pid": process.pid,
                "tmp_root": str(next_tmp_root),
                "output_dir": str(next_output_dir),
            },
        }
        if stop_after_launch:
            return launch_manifest
        current_round_index = next_round_index
        current_tmp_root = next_tmp_root
        current_output_dir = next_output_dir
        current_seed_path = current_seed_path


def _select_next_round_index(current_round_index: int, recommendation: str) -> int:
    """Choose the next configured CAPA round index from the current diagnosis.

    Args:
        current_round_index: Current round number, 1-based.
        recommendation: Analysis recommendation from `analyze_exp1_summary`.

    Returns:
        Next round index, capped to the explicit round list.
    """

    if recommendation == "retry-lower-threshold":
        return min(2, len(DEFAULT_EXP1_ROUNDS))
    if recommendation == "retry-detour-favoring":
        return min(3, len(DEFAULT_EXP1_ROUNDS))
    return min(current_round_index + 1, len(DEFAULT_EXP1_ROUNDS))


def _launch_next_round(
    seed_path: Path,
    tmp_root: Path,
    output_dir: Path,
    data_dir: Path,
    algorithms: Sequence[str],
    batch_size: int,
    local_couriers: int,
    platforms: int,
    couriers_per_platform: int,
    courier_capacity: float,
    service_radius_km: float,
    capa_runner_kwargs: dict[str, float],
) -> subprocess.Popen[str]:
    """Start one follow-up split round sharing the original canonical seed.

    Args:
        seed_path: Canonical seed bundle reused across rounds.
        tmp_root: Temp root for the new round.
        output_dir: Aggregate output directory for the new round.
        data_dir: Chengdu data directory.
        algorithms: Algorithms participating in the comparison.
        batch_size: Shared batch size in seconds.
        local_couriers: Local courier count.
        platforms: Cooperating platform count.
        couriers_per_platform: Couriers per cooperating platform.
        courier_capacity: Courier capacity.
        service_radius_km: Service radius in kilometers.
        capa_runner_kwargs: CAPA-only override set.

    Returns:
        Running subprocess handle for the launched round.
    """

    tmp_root.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "-u",
        str(Path(__file__).with_name("run_exp1_split.py")),
        "--tmp-root",
        str(tmp_root),
        "--output-dir",
        str(output_dir),
        "--seed-path",
        str(seed_path),
        "--data-dir",
        str(data_dir),
        "--batch-size",
        str(batch_size),
        "--local-couriers",
        str(local_couriers),
        "--platforms",
        str(platforms),
        "--couriers-per-platform",
        str(couriers_per_platform),
        "--courier-capacity",
        str(courier_capacity),
        "--service-radius-km",
        str(service_radius_km),
        "--algorithms",
        *list(algorithms),
        *_build_capa_override_cli(capa_runner_kwargs),
    ]
    stdout_handle = (tmp_root / "supervised_stdout.log").open("w", encoding="utf-8")
    stderr_handle = (tmp_root / "supervised_stderr.log").open("w", encoding="utf-8")
    try:
        process = subprocess.Popen(
            command,
            cwd=Path(__file__).resolve().parents[1],
            stdout=stdout_handle,
            stderr=stderr_handle,
            text=True,
        )
    finally:
        stdout_handle.close()
        stderr_handle.close()
    return process


def _build_capa_override_cli(capa_runner_kwargs: dict[str, float]) -> list[str]:
    """Translate CAPA override kwargs into split-run CLI flags.

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


def _append_supervisor_log_line(log_path: Path, snapshot: dict[str, Any], round_index: int) -> None:
    """Append one human-readable supervisor log line.

    Args:
        log_path: Append-only log path.
        snapshot: Collected split progress snapshot.
        round_index: Current managed round number.
    """

    point_parts = []
    for point_value in sorted(snapshot["points"], key=lambda value: int(value)):
        point = snapshot["points"][point_value]
        algorithms = ",".join(point["completed_algorithms"]) or "-"
        suffix = "done" if point["point_complete"] else "running"
        point_parts.append(f"{point_value}:algos={algorithms}:state={suffix}")
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(
            f"{datetime.now().isoformat(timespec='seconds')} round={round_index} "
            f"state={snapshot['state']} completed_points={snapshot['completed_points']}/{snapshot['total_points']} "
            f"{' | '.join(point_parts)}\n"
        )


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for the split Exp-1 supervisor."""

    parser = argparse.ArgumentParser(description="Supervise a split-process Exp-1 run and launch later CAPA rounds when needed.")
    parser.add_argument("--current-tmp-root", required=True)
    parser.add_argument("--current-output-dir", required=True)
    parser.add_argument("--snapshot-path", required=True)
    parser.add_argument("--log-path", required=True)
    parser.add_argument("--analysis-path", required=True)
    parser.add_argument("--data-dir", default="Data")
    parser.add_argument("--algorithms", nargs="+", default=list(DEFAULT_CHENGDU_PAPER_ALGORITHMS))
    parser.add_argument("--batch-size", type=int, default=30)
    parser.add_argument("--local-couriers", type=int, default=DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["local_couriers"])
    parser.add_argument("--platforms", type=int, default=DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["platforms"])
    parser.add_argument("--couriers-per-platform", type=int, default=DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["couriers_per_platform"])
    parser.add_argument("--courier-capacity", type=float, default=DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["courier_capacity"])
    parser.add_argument("--service-radius-km", type=float, default=DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["service_radius_km"])
    parser.add_argument("--poll-seconds", type=int, default=1800)
    parser.add_argument("--success-tr-ratio", type=float, default=0.9)
    parser.add_argument("--success-cr-gap", type=float, default=0.02)
    parser.add_argument("--max-rounds", type=int, default=len(DEFAULT_EXP1_ROUNDS))
    parser.add_argument("--next-tmp-root-base", default="/tmp/exp1_split_managed")
    parser.add_argument("--next-output-dir-base", default="outputs/plots/exp1_split_managed")
    return parser


def main() -> int:
    """Parse CLI arguments and start supervising one split Exp-1 run."""

    parser = build_parser()
    args = parser.parse_args()
    supervise_exp1_split(
        current_tmp_root=Path(args.current_tmp_root),
        current_output_dir=Path(args.current_output_dir),
        snapshot_path=Path(args.snapshot_path),
        log_path=Path(args.log_path),
        analysis_path=Path(args.analysis_path),
        data_dir=Path(args.data_dir),
        algorithms=args.algorithms,
        batch_size=args.batch_size,
        local_couriers=args.local_couriers,
        platforms=args.platforms,
        couriers_per_platform=args.couriers_per_platform,
        courier_capacity=args.courier_capacity,
        service_radius_km=args.service_radius_km,
        poll_seconds=args.poll_seconds,
        success_tr_ratio=args.success_tr_ratio,
        success_cr_gap=args.success_cr_gap,
        max_rounds=args.max_rounds,
        next_tmp_root_base=Path(args.next_tmp_root_base),
        next_output_dir_base=Path(args.next_output_dir_base),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
