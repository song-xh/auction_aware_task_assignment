"""Orchestrate CAPA mu / ratio sensitivity sweeps in lambda-mode.

Design (light cross)
--------------------
For each preset (formal@50000, ny@5000), at the tuned (lambda_c, lambda_p):
  * mu-sweep at r=0.5:  mu in {0.5, 0.6, 0.7, 0.8, 0.9}
  * r-sweep at mu=0.7:  r in {0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8}
The shared point (mu=0.7, r=0.5) is run once and reused across both axes.

formal points run SERIALLY (memory cap); ny points run in PARALLEL.
All points reuse the per-preset canonical seed so parcels/partner history are
identical across the grid.

Reuses build_point_command / run_subprocess / seed_path_for from the exp1 suite.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from capa.config import DEFAULT_MU_SENSITIVITY_LAMBDA_C, DEFAULT_MU_SENSITIVITY_LAMBDA_P
from scripts.run_capa_exp1_sensitivity_suite import (
    OUT_ROOT,
    build_point_command,
    run_subprocess,
)

MU_VALUES: tuple[float, ...] = (0.5, 0.6, 0.7, 0.8, 0.9)
R_VALUES: tuple[float, ...] = (0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8)
DEFAULT_MU = 0.7
DEFAULT_R = 0.5
SENS_POINTS: dict[str, int] = {"formal": 50000, "ny": 5000}


def _lambda_args(lambda_c: float, lambda_p: float) -> list[str]:
    """Build the fixed lambda CLI args shared by every point."""

    return [
        "--courier-lambda-c",
        str(lambda_c),
        "--platform-lambda-p",
        str(lambda_p),
    ]


def _point_args(mu: float, r: float, lambda_c: float, lambda_p: float) -> list[str]:
    """Build the per-point CAPA override CLI args."""

    return [
        "--total-sharing-rate-mu",
        str(mu),
        "--sharing-ratio-r",
        str(r),
        *_lambda_args(lambda_c, lambda_p),
    ]


def build_grid(lambda_c: float, lambda_p: float) -> list[tuple[str, float, float]]:
    """Build the (label, mu, r) grid: mu-sweep at r=0.5 + r-sweep at mu=0.7, deduped."""

    grid: list[tuple[str, float, float]] = []
    seen: set[tuple[float, float]] = set()
    for mu in MU_VALUES:
        key = (round(mu, 6), round(DEFAULT_R, 6))
        if key not in seen:
            seen.add(key)
            grid.append((f"mu_{mu}_r_{DEFAULT_R}", mu, DEFAULT_R))
    for r in R_VALUES:
        key = (round(DEFAULT_MU, 6), round(r, 6))
        if key not in seen:
            seen.add(key)
            grid.append((f"mu_{DEFAULT_MU}_r_{r}", DEFAULT_MU, r))
    return grid


def _worker(args: tuple[list[str], Path, str]) -> tuple[str, int]:
    """ProcessPool worker for parallel ny points."""

    command, log_dir, label = args
    rc = run_subprocess(command, log_dir, label)
    return label, rc


def run_preset(preset: str, lambda_c: float, lambda_p: float, log_dir: Path) -> dict[str, Path]:
    """Run the full mu/r grid for one preset. Serial for formal, parallel for ny."""

    point = SENS_POINTS[preset]
    out_root = OUT_ROOT / f"sens_mu_{preset}_{point}"
    out_root.mkdir(parents=True, exist_ok=True)
    grid = build_grid(lambda_c, lambda_p)
    point_dirs: dict[str, Path] = {label: out_root / label for label, _, _ in grid}

    if preset == "formal":
        for label, mu, r in grid:
            cmd = build_point_command(preset, point, point_dirs[label], extra_capa_args=_point_args(mu, r, lambda_c, lambda_p))
            print(f"[mu-sens][formal] start {label}", flush=True)
            rc = run_subprocess(cmd, log_dir, f"formal_{label}")
            print(f"[mu-sens][formal] {label} rc={rc}", flush=True)
            if rc != 0:
                raise RuntimeError(f"formal {label} failed (rc={rc}); see {log_dir}/formal_{label}.*.log")
    else:
        tasks: list[tuple[list[str], Path, str]] = []
        for label, mu, r in grid:
            cmd = build_point_command(preset, point, point_dirs[label], extra_capa_args=_point_args(mu, r, lambda_c, lambda_p))
            tasks.append((cmd, log_dir, f"ny_{label}"))
        max_workers = min(len(tasks), os.cpu_count() or 4)
        print(f"[mu-sens][ny] parallel max_workers={max_workers}", flush=True)
        with ProcessPoolExecutor(max_workers=max_workers) as pool:
            for label, rc in pool.map(_worker, tasks):
                print(f"[mu-sens][ny] {label} rc={rc}", flush=True)
                if rc != 0:
                    raise RuntimeError(f"{label} failed; see {log_dir}/{label}.*.log")
    return point_dirs


def aggregate(preset: str, point_dirs: dict[str, Path], out_root: Path) -> dict:
    """Read TR/CR per point and split into mu-curve (r=0.5) and r-curve (mu=0.7)."""

    def read_metrics(summary_path: Path) -> dict[str, float]:
        with summary_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        capa = data["capa"] if "capa" in data else data
        m = capa.get("metrics", {})
        return {k: float(m[k]) for k in ("TR", "local_TR", "cross_TR", "CR") if k in m}

    mu_curve: list[dict] = []
    r_curve: list[dict] = []
    for label, path in point_dirs.items():
        metrics = read_metrics(path / "summary.json")
        if label.endswith(f"r_{DEFAULT_R}"):
            mu = float(label.split("_")[1])
            mu_curve.append({"mu": mu, **metrics})
        if label.startswith(f"mu_{DEFAULT_MU}_"):
            r = float(label.split("_")[-1])
            r_curve.append({"r": r, **metrics})
    mu_curve.sort(key=lambda d: d["mu"])
    r_curve.sort(key=lambda d: d["r"])
    summary = {"preset": preset, "point": SENS_POINTS[preset], "mu_curve_at_r0.5": mu_curve, "r_curve_at_mu0.7": r_curve}
    (out_root / f"aggregate_{preset}.json").write_text(json.dumps(summary, indent=2))
    return summary


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse suite CLI arguments."""

    parser = argparse.ArgumentParser(description="CAPA mu/ratio sensitivity suite.")
    parser.add_argument("--presets", type=str, default="ny,formal", help="Comma-separated presets to run.")
    parser.add_argument("--courier-lambda-c", type=float, default=DEFAULT_MU_SENSITIVITY_LAMBDA_C)
    parser.add_argument("--platform-lambda-p", type=float, default=DEFAULT_MU_SENSITIVITY_LAMBDA_P)
    parser.add_argument("--log-dir", type=str, default="outputs/plots/sens_mu_logs")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the mu/ratio sensitivity suite for the requested presets."""

    args = parse_args(argv)
    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    presets = [p.strip() for p in args.presets.split(",") if p.strip()]
    for preset in presets:
        print(f"[mu-sens] === preset {preset} (point={SENS_POINTS[preset]}) ===", flush=True)
        point_dirs = run_preset(preset, args.courier_lambda_c, args.platform_lambda_p, log_dir)
        out_root = OUT_ROOT / f"sens_mu_{preset}_{SENS_POINTS[preset]}"
        summary = aggregate(preset, point_dirs, out_root)
        print(f"[mu-sens] {preset} aggregate: {json.dumps(summary, indent=2)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
