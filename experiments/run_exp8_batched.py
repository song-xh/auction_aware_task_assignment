"""Run Exp-8 deadline-noise sweep with at most 3 parallel points at a time.

Usage:
    python -m experiments.run_exp8_batched --scale 5000p [options]
    python -m experiments.run_exp8_batched --scale 50000p [options]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from env.chengdu import ChengduEnvironment
from experiments.deadline_disturbance import DEADLINE_NOISE_AXIS, DEADLINE_NOISE_VALUES
from experiments.paper_chengdu import DEFAULT_CHENGDU_PAPER_FIXED_CONFIG
from experiments.seeding import build_environment_seed, save_environment_seed

SCALE_CONFIGS = {
    "5000p": {
        "num_parcels": 5000,
        "local_couriers": 300,
        "platforms": 4,
        "couriers_per_platform": 50,
        "task_window_start_seconds": 0,
        "task_window_end_seconds": 900,
        "delay_window": (300.0, 600.0),
        "partner_history_task_count_start": 2000,
        "partner_history_task_count_step": 0,
        "tmp_root": Path("/tmp/chengdu_exp8_5000p_batched"),
        "default_output": Path("outputs/plots/exp8_capa_5000p_noise_sweep"),
    },
    "50000p": {
        "num_parcels": 50000,
        "local_couriers": 3000,
        "platforms": 4,
        "couriers_per_platform": 200,
        "task_window_start_seconds": 0,
        "task_window_end_seconds": 1800,
        "delay_window": (300.0, 900.0),
        "partner_history_task_count_start": 2000,
        "partner_history_task_count_step": 0,
        "tmp_root": Path("/tmp/chengdu_exp8_50000p_batched"),
        "default_output": Path("outputs/plots/exp8_capa_50000p_noise_sweep"),
    },
}

NOISE_VALUES = list(DEADLINE_NOISE_VALUES)  # [-20, -15, -10, -5, 0, 5, 10, 15, 20]
BATCH_SIZE = 3


def _token(value: int | float) -> str:
    text = str(value)
    return text.replace("-", "neg").replace(".", "_")


def _build_seed(scale_cfg: dict, batch_size: int) -> Path:
    """Build canonical seed for the given scale config."""
    seed_path = scale_cfg["tmp_root"] / "canonical_seed.pkl"
    if seed_path.exists():
        print(f"[seed] Reusing existing seed at {seed_path}", flush=True)
        return seed_path
    print(f"[seed] Building canonical environment...", flush=True)
    fixed = dict(DEFAULT_CHENGDU_PAPER_FIXED_CONFIG)
    fixed.update({
        "num_parcels": scale_cfg["num_parcels"],
        "local_couriers": scale_cfg["local_couriers"],
        "platforms": scale_cfg["platforms"],
        "couriers_per_platform": scale_cfg["couriers_per_platform"],
        "task_window_start_seconds": scale_cfg["task_window_start_seconds"],
        "task_window_end_seconds": scale_cfg["task_window_end_seconds"],
        "partner_history_task_count_start": scale_cfg["partner_history_task_count_start"],
        "partner_history_task_count_step": scale_cfg["partner_history_task_count_step"],
    })
    env = ChengduEnvironment.build(
        data_dir=Path(fixed["data_dir"]),
        num_parcels=int(fixed["num_parcels"]),
        local_courier_count=int(fixed["local_couriers"]),
        cooperating_platform_count=int(fixed["platforms"]),
        couriers_per_platform=int(fixed["couriers_per_platform"]),
        service_radius_km=fixed.get("service_radius_km"),
        courier_capacity=fixed.get("courier_capacity"),
        task_window_start_seconds=fixed.get("task_window_start_seconds"),
        task_window_end_seconds=fixed.get("task_window_end_seconds"),
        task_sampling_seed=int(fixed["task_sampling_seed"]),
        partner_history_task_count_start=int(fixed["partner_history_task_count_start"]),
        partner_history_task_count_step=int(fixed["partner_history_task_count_step"]),
        courier_alpha=float(fixed["courier_alpha"]),
        courier_service_score=float(fixed["courier_service_score"]),
        platform_quality_start=float(fixed["platform_quality_start"]),
        platform_quality_step=float(fixed["platform_quality_step"]),
    )
    seed_path.parent.mkdir(parents=True, exist_ok=True)
    save_environment_seed(build_environment_seed(env), seed_path)
    print(f"[seed] Saved to {seed_path}", flush=True)
    return seed_path


def _point_command(
    noise_value: int | float,
    output_dir: Path,
    seed_path: Path,
    scale_cfg: dict,
    batch_size: int,
    script_path: Path,
) -> list[str]:
    """Build the point-mode subprocess command for one noise value."""
    dw_start, dw_end = scale_cfg["delay_window"]
    cmd = [
        sys.executable, "-u",
        str(script_path),
        "--execution-mode", "point",
        "--point-value", str(noise_value),
        "--output-dir", str(output_dir),
        "--algorithms", "capa",
        "--num-parcels", str(scale_cfg["num_parcels"]),
        "--local-couriers", str(scale_cfg["local_couriers"]),
        "--platforms", str(scale_cfg["platforms"]),
        "--couriers-per-platform", str(scale_cfg["couriers_per_platform"]),
        "--task-window-start-seconds", str(scale_cfg["task_window_start_seconds"]),
        "--task-window-end-seconds", str(scale_cfg["task_window_end_seconds"]),
        "--delay-window", f"{dw_start},{dw_end}",
        "--partner-history-task-count-start", str(scale_cfg["partner_history_task_count_start"]),
        "--partner-history-task-count-step", str(scale_cfg["partner_history_task_count_step"]),
        "--batch-size", str(batch_size),
        "--service-radius-km", "1.0",
        "--seed-path", str(seed_path),
        "--data-dir", "Data",
    ]
    return cmd


def _run_batch(
    batch: list[int | float],
    tmp_root: Path,
    seed_path: Path,
    scale_cfg: dict,
    batch_size: int,
    script_path: Path,
    log_path: Path,
) -> dict[int | float, Path]:
    """Launch one batch of point subprocesses and wait for all to finish.

    Returns mapping from noise_value → point output dir.
    """
    point_dirs: dict[int | float, Path] = {}
    processes: dict[int | float, subprocess.Popen[str]] = {}

    for value in batch:
        out_dir = tmp_root / f"point_{_token(value)}"
        out_dir.mkdir(parents=True, exist_ok=True)
        point_dirs[value] = out_dir
        cmd = _point_command(value, out_dir, seed_path, scale_cfg, batch_size, script_path)
        stdout_h = (out_dir / "stdout.log").open("w", encoding="utf-8")
        stderr_h = (out_dir / "stderr.log").open("w", encoding="utf-8")
        proc = subprocess.Popen(cmd, cwd=Path(__file__).resolve().parents[1], stdout=stdout_h, stderr=stderr_h, text=True)
        processes[value] = proc
        msg = f"[batch] Launched noise={value} pid={proc.pid}"
        print(msg, flush=True)
        with log_path.open("a") as lf:
            lf.write(msg + "\n")

    while processes:
        done = [v for v, p in processes.items() if p.poll() is not None]
        for v in done:
            proc = processes.pop(v)
            status = "OK" if proc.returncode == 0 else f"FAILED(rc={proc.returncode})"
            msg = f"[batch] noise={v} {status}"
            print(msg, flush=True)
            with log_path.open("a") as lf:
                lf.write(msg + "\n")
            if proc.returncode != 0:
                stderr_text = (point_dirs[v] / "stderr.log").read_text(encoding="utf-8", errors="replace")[-2000:]
                raise RuntimeError(f"Point noise={v} failed (rc={proc.returncode}):\n{stderr_text}")
        if processes:
            time.sleep(10)

    return point_dirs


def _aggregate(
    all_point_dirs: dict[int | float, Path],
    output_dir: Path,
    algorithms: list[str],
    log_path: Path,
) -> dict:
    """Aggregate finished point summaries into one sweep summary."""
    runs = []
    for value in sorted(all_point_dirs):
        summary_path = all_point_dirs[value] / "summary.json"
        with summary_path.open("r", encoding="utf-8") as fh:
            runs.append(json.load(fh))
    summary = {
        "sweep_parameter": DEADLINE_NOISE_AXIS,
        "algorithms": algorithms,
        "runs": runs,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "summary.json").open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    from experiments.plotting import save_comparison_plots
    save_comparison_plots(summary=summary, output_dir=output_dir)
    msg = f"[agg] Summary saved to {output_dir / 'summary.json'}"
    print(msg, flush=True)
    with log_path.open("a") as lf:
        lf.write(msg + "\n")
    return summary


def main() -> int:
    """Parse args, build seed, run batched points, aggregate."""
    parser = argparse.ArgumentParser(description="Batched Exp-8 runner (3 points at a time).")
    parser.add_argument("--scale", choices=list(SCALE_CONFIGS.keys()), required=True)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--batch-size", type=int, default=30, help="CAPA batch size (parcels per batch window).")
    parser.add_argument("--max-parallel", type=int, default=BATCH_SIZE, help="Max parallel point subprocesses.")
    args = parser.parse_args()

    scale_cfg = SCALE_CONFIGS[args.scale]
    output_dir = Path(args.output_dir) if args.output_dir else scale_cfg["default_output"]
    tmp_root = scale_cfg["tmp_root"]
    tmp_root.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    log_path = output_dir / "batched_run.log"
    log_path.write_text(f"Exp-8 batched run: scale={args.scale}\n", encoding="utf-8")

    script_path = Path(__file__).resolve().parent / "run_chengdu_exp8_deadline_noise.py"

    seed_path = _build_seed(scale_cfg, args.batch_size)

    all_point_dirs: dict[int | float, Path] = {}
    batches = [NOISE_VALUES[i:i + args.max_parallel] for i in range(0, len(NOISE_VALUES), args.max_parallel)]

    for batch_idx, batch in enumerate(batches):
        msg = f"[run] Batch {batch_idx + 1}/{len(batches)}: noise values {batch}"
        print(msg, flush=True)
        with log_path.open("a") as lf:
            lf.write(msg + "\n")
        point_dirs = _run_batch(batch, tmp_root, seed_path, scale_cfg, args.batch_size, script_path, log_path)
        all_point_dirs.update(point_dirs)

    _aggregate(all_point_dirs, output_dir, ["capa"], log_path)
    print("[done] All batches complete.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
