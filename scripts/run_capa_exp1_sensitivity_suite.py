"""Orchestrate exp1 rerun + zeta/omega sensitivity sweeps for CAPA.

Stages
------
A. exp1 num_parcels (capa only)
   - formal points run SERIALLY to cap memory.
   - ny points run in PARALLEL (small dataset).
B. zeta sensitivity at formal/50000 + ny/5000.
   1. Run baseline (dynamic threshold, zeta=0.2, omega=0.8). Read summary
      to extract `final_local_revenue_threshold = Th*`.
   2. Re-run with FIXED threshold = Th* and zeta in {0.1, 0.3, 0.4, 0.5}.
C. omega sensitivity at formal/50000 + ny/5000.
   - Vary omega in {0.5, 0.6, 0.7, 0.8, 0.9, 1.0} keeping dynamic threshold.

All runs share the same canonical seed per preset so parcels and partner
history are identical across stages.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
SHARED_POOL = REPO_ROOT / "outputs" / "shared_pool"
OUT_ROOT = REPO_ROOT / "outputs" / "plots"

FORMAL_POINTS: tuple[int, ...] = (5000, 20000, 50000, 100000, 200000)
NY_POINTS: tuple[int, ...] = (500, 2000, 5000, 10000, 20000)

ZETA_VARIANTS: tuple[float, ...] = (0.1, 0.3, 0.4, 0.5)
OMEGA_VARIANTS: tuple[float, ...] = (0.5, 0.6, 0.7, 0.8, 0.9, 1.0)

BASELINE_ZETA = 0.2
BASELINE_OMEGA = 0.8

SENS_POINTS: dict[str, int] = {"formal": 50000, "ny": 5000}


def seed_path_for(preset: str) -> Path:
    """Return canonical seed path for the preset."""

    return SHARED_POOL / preset / "canonical_seed.pkl"


def build_point_command(
    preset: str,
    point_value: int,
    output_dir: Path,
    extra_capa_args: Sequence[str] = (),
) -> list[str]:
    """Build subprocess command for one CAPA exp1 point.

    Args:
        preset: Preset name.
        point_value: num_parcels axis value.
        output_dir: Per-run output directory.
        extra_capa_args: CAPA parameter overrides (omega, zeta, fixed threshold).
    """

    command = [
        sys.executable,
        "-u",
        "-m",
        "experiments.run_chengdu_exp1_num_parcels",
        "--execution-mode",
        "point",
        "--preset",
        preset,
        "--point-value",
        str(point_value),
        "--algorithms",
        "capa",
        "--seed-path",
        str(seed_path_for(preset)),
        "--output-dir",
        str(output_dir),
    ]
    command.extend(extra_capa_args)
    return command


def run_subprocess(command: list[str], log_dir: Path, label: str) -> int:
    """Run one subprocess, streaming stdout/stderr to log files."""

    log_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = log_dir / f"{label}.stdout.log"
    stderr_path = log_dir / f"{label}.stderr.log"
    with stdout_path.open("w", encoding="utf-8") as stdout_handle, stderr_path.open(
        "w", encoding="utf-8"
    ) as stderr_handle:
        process = subprocess.Popen(
            command,
            cwd=str(REPO_ROOT),
            stdout=stdout_handle,
            stderr=stderr_handle,
            text=True,
        )
        return process.wait()


def _ny_worker(args: tuple[list[str], Path, str]) -> tuple[str, int]:
    """ProcessPool worker for ny parallel points."""

    command, log_dir, label = args
    rc = run_subprocess(command, log_dir, label)
    return label, rc


def run_stage_a(preset: str, log_dir: Path) -> dict[int, Path]:
    """Run exp1 capa across preset points; serial for formal, parallel for ny."""

    out_dir = OUT_ROOT / f"exp1_capa_{preset}_rerun"
    out_dir.mkdir(parents=True, exist_ok=True)
    points = FORMAL_POINTS if preset == "formal" else NY_POINTS
    point_dirs: dict[int, Path] = {p: out_dir / f"point_{p}" for p in points}

    if preset == "formal":
        for p in points:
            label = f"A_formal_{p}"
            cmd = build_point_command(preset, p, point_dirs[p])
            print(f"[stage A][formal] start point {p}", flush=True)
            rc = run_subprocess(cmd, log_dir, label)
            print(f"[stage A][formal] point {p} rc={rc}", flush=True)
            if rc != 0:
                raise RuntimeError(f"formal point {p} failed (rc={rc}); see {log_dir}/{label}.*.log")
    else:
        tasks: list[tuple[list[str], Path, str]] = []
        for p in points:
            label = f"A_ny_{p}"
            cmd = build_point_command(preset, p, point_dirs[p])
            tasks.append((cmd, log_dir, label))
        max_workers = min(len(tasks), os.cpu_count() or 5)
        print(f"[stage A][ny] parallel max_workers={max_workers}", flush=True)
        with ProcessPoolExecutor(max_workers=max_workers) as pool:
            for label, rc in pool.map(_ny_worker, tasks):
                print(f"[stage A][ny] {label} rc={rc}", flush=True)
                if rc != 0:
                    raise RuntimeError(f"{label} failed; see {log_dir}/{label}.*.log")
    return point_dirs


def read_final_threshold(summary_path: Path) -> float:
    """Read final_local_revenue_threshold from a point summary file."""

    with summary_path.open("r", encoding="utf-8") as handle:
        summary = json.load(handle)
    capa = summary["capa"] if "capa" in summary else summary
    metrics = capa.get("metrics", {})
    if "final_local_revenue_threshold" not in metrics:
        raise KeyError(
            f"final_local_revenue_threshold missing in {summary_path}; "
            f"keys={list(metrics.keys())}"
        )
    return float(metrics["final_local_revenue_threshold"])


def run_stage_b(preset: str, log_dir: Path) -> dict[str, Path]:
    """Run zeta sensitivity. Baseline first → Th* → 4 fixed-threshold variants."""

    point = SENS_POINTS[preset]
    out_root = OUT_ROOT / f"sens_zeta_{preset}_{point}"
    out_root.mkdir(parents=True, exist_ok=True)
    runs: dict[str, Path] = {}

    baseline_dir = out_root / "baseline"
    baseline_label = f"B_{preset}_baseline"
    baseline_cmd = build_point_command(
        preset,
        point,
        baseline_dir,
        extra_capa_args=[
            "--local-payment-ratio-zeta",
            str(BASELINE_ZETA),
            "--threshold-omega",
            str(BASELINE_OMEGA),
        ],
    )
    print(f"[stage B][{preset}] baseline start", flush=True)
    rc = run_subprocess(baseline_cmd, log_dir, baseline_label)
    if rc != 0:
        raise RuntimeError(f"baseline {preset} failed (rc={rc})")
    runs["baseline"] = baseline_dir

    th_star = read_final_threshold(baseline_dir / "summary.json")
    print(f"[stage B][{preset}] Th*={th_star:.6f}", flush=True)
    (out_root / "th_star.json").write_text(
        json.dumps({"preset": preset, "point": point, "final_local_revenue_threshold": th_star}, indent=2)
    )

    for zeta in ZETA_VARIANTS:
        sub_dir = out_root / f"zeta_{zeta}"
        label = f"B_{preset}_zeta_{zeta}"
        cmd = build_point_command(
            preset,
            point,
            sub_dir,
            extra_capa_args=[
                "--local-payment-ratio-zeta",
                str(zeta),
                "--threshold-omega",
                str(BASELINE_OMEGA),
                "--fixed-local-revenue-threshold",
                str(th_star),
            ],
        )
        print(f"[stage B][{preset}] zeta={zeta} start", flush=True)
        rc = run_subprocess(cmd, log_dir, label)
        if rc != 0:
            raise RuntimeError(f"{label} failed (rc={rc})")
        runs[f"zeta_{zeta}"] = sub_dir
    return runs


def run_stage_c(preset: str, log_dir: Path) -> dict[str, Path]:
    """Run omega sensitivity. Dynamic threshold; vary omega only."""

    point = SENS_POINTS[preset]
    out_root = OUT_ROOT / f"sens_omega_{preset}_{point}"
    out_root.mkdir(parents=True, exist_ok=True)
    runs: dict[str, Path] = {}
    for omega in OMEGA_VARIANTS:
        sub_dir = out_root / f"omega_{omega}"
        label = f"C_{preset}_omega_{omega}"
        cmd = build_point_command(
            preset,
            point,
            sub_dir,
            extra_capa_args=[
                "--local-payment-ratio-zeta",
                str(BASELINE_ZETA),
                "--threshold-omega",
                str(omega),
            ],
        )
        print(f"[stage C][{preset}] omega={omega} start", flush=True)
        rc = run_subprocess(cmd, log_dir, label)
        if rc != 0:
            raise RuntimeError(f"{label} failed (rc={rc})")
        runs[f"omega_{omega}"] = sub_dir
    return runs


STAGE_RUNNERS = {
    "A_formal": lambda log: run_stage_a("formal", log),
    "A_ny": lambda log: run_stage_a("ny", log),
    "B_formal": lambda log: run_stage_b("formal", log),
    "B_ny": lambda log: run_stage_b("ny", log),
    "C_formal": lambda log: run_stage_c("formal", log),
    "C_ny": lambda log: run_stage_c("ny", log),
}

DEFAULT_STAGE_ORDER: tuple[str, ...] = (
    "A_formal",
    "A_ny",
    "B_formal",
    "B_ny",
    "C_formal",
    "C_ny",
)


def main() -> int:
    """Parse CLI and run requested stages sequentially."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stages",
        nargs="+",
        default=list(DEFAULT_STAGE_ORDER),
        choices=list(STAGE_RUNNERS.keys()),
    )
    parser.add_argument(
        "--log-dir",
        default=str(OUT_ROOT / "capa_sensitivity_logs"),
    )
    args = parser.parse_args()
    log_dir = Path(args.log_dir)
    for stage in args.stages:
        print(f"\n========== STAGE {stage} ==========", flush=True)
        STAGE_RUNNERS[stage](log_dir)
        print(f"========== STAGE {stage} DONE ==========\n", flush=True)
    print("ALL STAGES DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
