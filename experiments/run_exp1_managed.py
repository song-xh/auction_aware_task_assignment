"""Run Chengdu paper experiment 1 under managed multi-round supervision."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from dataclasses import asdict, dataclass
from functools import partial
from pathlib import Path
from statistics import mean
from time import time
from typing import Any, Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from algorithms.registry import build_algorithm_runner
from experiments.compare import run_comparison_sweep
from experiments.paper_chengdu import DEFAULT_CHENGDU_PAPER_FIXED_CONFIG
from experiments.paper_config import DEFAULT_CHENGDU_PAPER_ALGORITHMS, PAPER_SUITE_PRESETS


@dataclass(frozen=True)
class Exp1RoundSpec:
    """Define one explicit CAPA parameterization candidate for managed Exp-1 runs."""

    name: str
    rationale: str
    capa_runner_kwargs: dict[str, float]


DEFAULT_EXP1_ROUNDS: tuple[Exp1RoundSpec, ...] = (
    Exp1RoundSpec(
        name="paper-default",
        rationale="Paper-default CAPA parameters.",
        capa_runner_kwargs={
            "utility_balance_gamma": 0.5,
            "threshold_omega": 1.0,
            "local_payment_ratio_zeta": 0.2,
            "local_sharing_rate_mu1": 0.5,
            "cross_platform_sharing_rate_mu2": 0.4,
        },
    ),
    Exp1RoundSpec(
        name="lower-threshold",
        rationale="Lower Eq.7 threshold to keep more feasible parcels in local matching when CR lags.",
        capa_runner_kwargs={
            "utility_balance_gamma": 0.5,
            "threshold_omega": 0.8,
            "local_payment_ratio_zeta": 0.2,
            "local_sharing_rate_mu1": 0.5,
            "cross_platform_sharing_rate_mu2": 0.4,
        },
    ),
    Exp1RoundSpec(
        name="detour-favoring",
        rationale="Favor detour efficiency while keeping the lower threshold when TR still lags.",
        capa_runner_kwargs={
            "utility_balance_gamma": 0.3,
            "threshold_omega": 0.8,
            "local_payment_ratio_zeta": 0.2,
            "local_sharing_rate_mu1": 0.5,
            "cross_platform_sharing_rate_mu2": 0.4,
        },
    ),
)


def build_managed_exp1_runner(
    algorithm_name: str,
    capa_runner_kwargs: dict[str, float] | None = None,
    **kwargs: object,
) -> Any:
    """Build one algorithm runner for managed Exp-1 rounds.

    Args:
        algorithm_name: Unified algorithm identifier.
        capa_runner_kwargs: Optional CAPA-specific override set for the current round.
        **kwargs: Normal experiment-layer runner arguments.

    Returns:
        One unified algorithm runner instance.
    """

    if algorithm_name == "capa":
        merged_kwargs = dict(kwargs)
        merged_kwargs.update(capa_runner_kwargs or {})
        return build_algorithm_runner("capa", **merged_kwargs)
    return build_algorithm_runner(algorithm_name, **kwargs)


def analyze_exp1_summary(
    summary: dict[str, Any],
    algorithms: Sequence[str],
    round_spec: Exp1RoundSpec,
    success_tr_ratio: float,
    success_cr_gap: float,
) -> dict[str, Any]:
    """Score one Exp-1 round and decide whether CAPA is competitive enough to keep.

    Args:
        summary: Comparison sweep summary produced by `run_comparison_sweep`.
        algorithms: Ordered algorithm list participating in the round.
        round_spec: Current CAPA parameterization.
        success_tr_ratio: Minimum CAPA TR ratio versus the strongest baseline.
        success_cr_gap: Maximum allowed CAPA CR drop versus the strongest baseline.

    Returns:
        Analysis payload describing CAPA competitiveness and next-step recommendation.
    """

    runs = summary["runs"]
    capa_tr_values = [float(run["capa"]["metrics"]["TR"]) for run in runs]
    capa_cr_values = [float(run["capa"]["metrics"]["CR"]) for run in runs]
    capa_bpt_values = [float(run["capa"]["metrics"]["BPT"]) for run in runs]
    baseline_algorithms = [name for name in algorithms if name != "capa"]
    baseline_scores: dict[str, dict[str, float]] = {}
    for algorithm in baseline_algorithms:
        baseline_scores[algorithm] = {
            "avg_TR": mean(float(run[algorithm]["metrics"]["TR"]) for run in runs),
            "avg_CR": mean(float(run[algorithm]["metrics"]["CR"]) for run in runs),
            "avg_BPT": mean(float(run[algorithm]["metrics"]["BPT"]) for run in runs),
        }

    capa_scores = {
        "avg_TR": mean(capa_tr_values),
        "avg_CR": mean(capa_cr_values),
        "avg_BPT": mean(capa_bpt_values),
    }
    best_baseline_tr = max((score["avg_TR"] for score in baseline_scores.values()), default=0.0)
    best_baseline_cr = max((score["avg_CR"] for score in baseline_scores.values()), default=0.0)
    tr_ratio = 1.0 if best_baseline_tr <= 0 else capa_scores["avg_TR"] / best_baseline_tr
    cr_gap = best_baseline_cr - capa_scores["avg_CR"]
    accepted = tr_ratio >= success_tr_ratio and cr_gap <= success_cr_gap

    if accepted:
        recommendation = "accept"
        diagnosis = "CAPA remains competitive on both revenue and completion rate under the managed threshold."
    elif cr_gap > success_cr_gap:
        recommendation = "retry-lower-threshold"
        diagnosis = (
            "CAPA completion rate lags the strongest baseline. "
            "The most likely issue is that Eq.7 is pushing too many parcels out of local matching, so the next round lowers omega."
        )
    else:
        recommendation = "retry-detour-favoring"
        diagnosis = (
            "CAPA completion stays close to the strongest baseline but total revenue lags. "
            "The next round shifts utility weight toward detour efficiency while keeping a lower threshold."
        )

    return {
        "round": asdict(round_spec),
        "accepted": accepted,
        "recommendation": recommendation,
        "diagnosis": diagnosis,
        "capa_scores": capa_scores,
        "baseline_scores": baseline_scores,
        "best_baseline_TR": best_baseline_tr,
        "best_baseline_CR": best_baseline_cr,
        "tr_ratio_vs_best_baseline": tr_ratio,
        "cr_gap_vs_best_baseline": cr_gap,
    }


def promote_round_results(round_output_dir: Path, final_output_dir: Path) -> None:
    """Copy the selected round result directory into the final result location.

    Args:
        round_output_dir: Round directory under the temporary root.
        final_output_dir: Final destination directory for the accepted round.
    """

    if final_output_dir.exists():
        raise FileExistsError(f"Final output directory already exists: {final_output_dir}")
    final_output_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(round_output_dir, final_output_dir)


def run_managed_exp1(
    tmp_root: Path,
    final_output_dir: Path,
    algorithms: Sequence[str] = DEFAULT_CHENGDU_PAPER_ALGORITHMS,
    fixed_config_overrides: dict[str, Any] | None = None,
    preset_name: str = "formal",
    max_workers: int | None = None,
    batch_size: int = 30,
    round_specs: Sequence[Exp1RoundSpec] = DEFAULT_EXP1_ROUNDS,
    success_tr_ratio: float = 0.9,
    success_cr_gap: float = 0.02,
    parallel_backend: str = "thread",
) -> dict[str, Any]:
    """Run managed multi-round Chengdu Exp-1 and promote the winning CAPA round.

    Args:
        tmp_root: Temporary root where all round outputs and status files are written.
        final_output_dir: Final destination for the accepted round.
        algorithms: Algorithms participating in the comparison sweep.
        fixed_config_overrides: Optional overrides on top of the Chengdu paper defaults.
        preset_name: Parcel-count preset name.
        max_workers: Optional process count for parallel sweep-point execution.
        batch_size: Batch size in seconds for all rounds.
        round_specs: Ordered CAPA parameter candidates.
        success_tr_ratio: Minimum CAPA TR ratio versus the strongest baseline.
        success_cr_gap: Maximum allowed CAPA CR drop versus the strongest baseline.
        parallel_backend: Explicit sweep-point parallel backend used by the comparison runner.

    Returns:
        Final managed experiment manifest.
    """

    tmp_root.mkdir(parents=True, exist_ok=True)
    fixed_config = dict(DEFAULT_CHENGDU_PAPER_FIXED_CONFIG)
    if fixed_config_overrides:
        fixed_config.update(fixed_config_overrides)
    fixed_config["batch_size"] = batch_size
    parcel_values = PAPER_SUITE_PRESETS["chengdu-paper"][preset_name]["num_parcels"]
    status_path = tmp_root / "status.json"
    round_manifests: list[dict[str, Any]] = []
    managed_started_at = time()

    for round_index, round_spec in enumerate(round_specs, start=1):
        round_output_dir = tmp_root / f"round_{round_index:02d}_{round_spec.name}"
        round_output_dir.mkdir(parents=True, exist_ok=True)
        _write_status(
            status_path=status_path,
            payload={
                "pid": os.getpid(),
                "state": "running",
                "round_index": round_index,
                "round_name": round_spec.name,
                "round_output_dir": str(round_output_dir),
                "started_at": managed_started_at,
                "updated_at": time(),
            },
        )
        summary = run_comparison_sweep(
            algorithms=algorithms,
            output_dir=round_output_dir,
            sweep_parameter="num_parcels",
            sweep_values=parcel_values,
            fixed_config=fixed_config,
            runner_builder=partial(build_managed_exp1_runner, capa_runner_kwargs=round_spec.capa_runner_kwargs),
            max_workers=max_workers,
            parallel_backend=parallel_backend,
        )
        analysis = analyze_exp1_summary(
            summary=summary,
            algorithms=algorithms,
            round_spec=round_spec,
            success_tr_ratio=success_tr_ratio,
            success_cr_gap=success_cr_gap,
        )
        round_manifest = {
            "round_index": round_index,
            "round_name": round_spec.name,
            "round_output_dir": str(round_output_dir),
            "summary_path": str(round_output_dir / "summary.json"),
            "analysis": analysis,
        }
        round_manifests.append(round_manifest)
        with (round_output_dir / "analysis.json").open("w", encoding="utf-8") as handle:
            json.dump(analysis, handle, indent=2)
        with (round_output_dir / "round_manifest.json").open("w", encoding="utf-8") as handle:
            json.dump(round_manifest, handle, indent=2)

        if analysis["accepted"]:
            promote_round_results(round_output_dir=round_output_dir, final_output_dir=final_output_dir)
            final_manifest = {
                "accepted": True,
                "selected_round": round_manifest,
                "status_path": str(status_path),
                "rounds": round_manifests,
                "final_output_dir": str(final_output_dir),
            }
            with (tmp_root / "final_manifest.json").open("w", encoding="utf-8") as handle:
                json.dump(final_manifest, handle, indent=2)
            _write_status(
                status_path=status_path,
                payload={
                    "pid": os.getpid(),
                    "state": "accepted",
                    "round_index": round_index,
                    "round_name": round_spec.name,
                    "final_output_dir": str(final_output_dir),
                    "updated_at": time(),
                },
            )
            return final_manifest

    final_manifest = {
        "accepted": False,
        "selected_round": max(
            round_manifests,
            key=lambda item: (
                item["analysis"]["tr_ratio_vs_best_baseline"],
                -item["analysis"]["cr_gap_vs_best_baseline"],
            ),
        ) if round_manifests else None,
        "status_path": str(status_path),
        "rounds": round_manifests,
        "final_output_dir": str(final_output_dir),
    }
    with (tmp_root / "final_manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(final_manifest, handle, indent=2)
    _write_status(
        status_path=status_path,
        payload={
            "pid": os.getpid(),
            "state": "exhausted",
            "updated_at": time(),
            "final_output_dir": str(final_output_dir),
        },
    )
    return final_manifest


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for managed Exp-1 runs."""

    parser = argparse.ArgumentParser(description="Run managed Chengdu Exp-1 with CAPA retry rounds and monitoring manifests.")
    parser.add_argument("--tmp-root", default="/tmp/exp1_managed", help="Temporary root for per-round outputs and status files.")
    parser.add_argument("--final-output-dir", default="/tmp/exp1_selected", help="Final destination for the accepted round.")
    parser.add_argument("--data-dir", default="Data", help="Path to the Chengdu data directory.")
    parser.add_argument("--preset", default="formal", choices=tuple(PAPER_SUITE_PRESETS["chengdu-paper"].keys()))
    parser.add_argument("--algorithms", nargs="+", default=list(DEFAULT_CHENGDU_PAPER_ALGORITHMS))
    parser.add_argument("--max-workers", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=30)
    parser.add_argument("--num-parcels", type=int, default=DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["num_parcels"])
    parser.add_argument("--local-couriers", type=int, default=DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["local_couriers"])
    parser.add_argument("--platforms", type=int, default=DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["platforms"])
    parser.add_argument("--couriers-per-platform", type=int, default=DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["couriers_per_platform"])
    parser.add_argument("--courier-capacity", type=float, default=DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["courier_capacity"])
    parser.add_argument("--service-radius-km", type=float, default=DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["service_radius_km"])
    parser.add_argument("--success-tr-ratio", type=float, default=0.9)
    parser.add_argument("--success-cr-gap", type=float, default=0.02)
    parser.add_argument("--parallel-backend", default="thread", choices=("thread", "process"))
    return parser


def main() -> int:
    """Parse CLI arguments and execute the managed Exp-1 controller."""

    parser = build_parser()
    args = parser.parse_args()
    run_managed_exp1(
        tmp_root=Path(args.tmp_root),
        final_output_dir=Path(args.final_output_dir),
        algorithms=args.algorithms,
        fixed_config_overrides={
            "data_dir": Path(args.data_dir),
            "num_parcels": args.num_parcels,
            "local_couriers": args.local_couriers,
            "platforms": args.platforms,
            "couriers_per_platform": args.couriers_per_platform,
            "courier_capacity": args.courier_capacity,
            "service_radius_km": args.service_radius_km,
        },
        preset_name=args.preset,
        max_workers=args.max_workers,
        batch_size=args.batch_size,
        success_tr_ratio=args.success_tr_ratio,
        success_cr_gap=args.success_cr_gap,
        parallel_backend=args.parallel_backend,
    )
    return 0


def _write_status(status_path: Path, payload: dict[str, Any]) -> None:
    """Write one JSON status snapshot for external monitoring loops.

    Args:
        status_path: Output JSON file path.
        payload: Status payload.
    """

    with status_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


if __name__ == "__main__":
    raise SystemExit(main())
