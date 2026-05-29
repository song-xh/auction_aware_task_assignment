"""Small-sample lambda_c/lambda_p cross-sweep for CAPA mu sensitivity tuning.

Parses the road graph once, builds one canonical small environment, then clones
fresh mutable state per grid point so every (lambda_c, lambda_p, mu) run sees the
identical parcels/couriers. Records TR/CR per point to a JSON file.

Goal: pick (lambda_c, lambda_p) whose TR(mu) curve peaks at the default mu=0.7 and
falls at both mu=0.5 (platform refusal) and mu=0.9 (low local retention (1-mu)).

Example
-------
    python -m scripts.tune_capa_lambda \
        --lambda-c 0.2,0.3,0.4,0.5,0.6 --lambda-p 0.2,0.3,0.4,0.5 \
        --mu 0.5,0.6,0.7,0.8,0.9 --ratio-r 0.5 \
        --out outputs/mu_tuning/grid.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from algorithms.capa_runner import build_capa_runner
from env.chengdu import ChengduEnvironment
from experiments.paper_chengdu import build_preset_fixed_config
from experiments.seeding import build_environment_seed, clone_environment_from_seed


def _parse_floats(text: str) -> list[float]:
    """Parse a comma-separated float list."""

    return [float(value) for value in text.split(",") if value.strip()]


def build_small_seed(
    preset: str,
    num_parcels: int,
    local_couriers: int,
    platforms: int,
    couriers_per_platform: int,
    data_dir: Path,
):
    """Build one small canonical environment seed (single graph parse)."""

    fixed = build_preset_fixed_config(preset)
    environment = ChengduEnvironment.build(
        data_dir=data_dir,
        num_parcels=num_parcels,
        local_courier_count=local_couriers,
        cooperating_platform_count=platforms,
        couriers_per_platform=couriers_per_platform,
        service_radius_km=fixed["service_radius_km"],
        courier_capacity=fixed["courier_capacity"],
        task_window_start_seconds=fixed["task_window_start_seconds"],
        task_window_end_seconds=fixed["task_window_end_seconds"],
        task_sampling_seed=int(fixed["task_sampling_seed"]),
        partner_history_task_count_start=int(fixed["partner_history_task_count_start"]),
        partner_history_task_count_step=int(fixed["partner_history_task_count_step"]),
        courier_alpha=float(fixed["courier_alpha"]),
        courier_beta=fixed["courier_beta"],
        courier_service_score=float(fixed["courier_service_score"]),
        platform_quality_start=float(fixed["platform_quality_start"]),
        platform_quality_step=float(fixed["platform_quality_step"]),
        deadline_seconds=fixed.get("deadline_seconds"),
        courier_speed_kmh=fixed.get("courier_speed_kmh"),
    )
    return build_environment_seed(environment), int(fixed["batch_size"])


def run_point(seed, batch_size: int, lambda_c: float, lambda_p: float, mu: float, ratio_r: float) -> dict[str, float]:
    """Run one CAPA evaluation on a fresh clone and return TR/CR/cross_TR."""

    mu1 = ratio_r * mu
    mu2 = (1.0 - ratio_r) * mu
    runner = build_capa_runner(
        batch_size=batch_size,
        local_sharing_rate_mu1=mu1,
        cross_platform_sharing_rate_mu2=mu2,
        courier_expected_income_ratio_lambda_c=lambda_c,
        platform_expected_income_ratio_lambda_p=lambda_p,
    )
    environment = clone_environment_from_seed(seed)
    summary = runner.run(environment, output_dir=None)
    metrics = summary["metrics"]
    return {
        "TR": float(metrics["TR"]),
        "CR": float(metrics["CR"]),
        "cross_TR": float(metrics["cross_TR"]),
        "local_TR": float(metrics["local_TR"]),
    }


def main(argv: Sequence[str] | None = None) -> int:
    """Run the lambda cross-sweep and persist results."""

    parser = argparse.ArgumentParser(description="CAPA lambda_c/lambda_p tuning cross-sweep.")
    parser.add_argument("--lambda-c", type=str, required=True, help="Comma-separated lambda_c values.")
    parser.add_argument("--lambda-p", type=str, required=True, help="Comma-separated lambda_p values.")
    parser.add_argument("--mu", type=str, default="0.5,0.6,0.7,0.8,0.9", help="Comma-separated mu values.")
    parser.add_argument("--ratio-r", type=float, default=0.5, help="mu split ratio r (mu1=r*mu).")
    parser.add_argument("--preset", type=str, default="ny")
    parser.add_argument("--num-parcels", type=int, default=300)
    parser.add_argument("--local-couriers", type=int, default=20)
    parser.add_argument("--platforms", type=int, default=4)
    parser.add_argument("--couriers-per-platform", type=int, default=5)
    parser.add_argument("--data-dir", type=str, default="Data")
    parser.add_argument("--out", type=str, required=True, help="Output JSON path.")
    args = parser.parse_args(argv)

    lambda_c_values = _parse_floats(args.lambda_c)
    lambda_p_values = _parse_floats(args.lambda_p)
    mu_values = _parse_floats(args.mu)

    print(
        f"[tune] building small seed: preset={args.preset} parcels={args.num_parcels} "
        f"couriers={args.local_couriers} platforms={args.platforms} cpp={args.couriers_per_platform}",
        flush=True,
    )
    seed, batch_size = build_small_seed(
        preset=args.preset,
        num_parcels=args.num_parcels,
        local_couriers=args.local_couriers,
        platforms=args.platforms,
        couriers_per_platform=args.couriers_per_platform,
        data_dir=Path(args.data_dir),
    )

    results: list[dict[str, float]] = []
    total = len(lambda_c_values) * len(lambda_p_values) * len(mu_values)
    done = 0
    for lambda_c in lambda_c_values:
        for lambda_p in lambda_p_values:
            for mu in mu_values:
                point = run_point(seed, batch_size, lambda_c, lambda_p, mu, args.ratio_r)
                record = {"lambda_c": lambda_c, "lambda_p": lambda_p, "mu": mu, **point}
                results.append(record)
                done += 1
                print(
                    f"[tune] {done}/{total} lc={lambda_c} lp={lambda_p} mu={mu} "
                    f"TR={point['TR']:.2f} CR={point['CR']:.3f}",
                    flush=True,
                )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        json.dump({"ratio_r": args.ratio_r, "results": results}, handle, indent=2)
    print(f"[tune] wrote {len(results)} records to {out_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
