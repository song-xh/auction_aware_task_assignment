"""Train RL-CAPA, infer with the saved checkpoint, and benchmark against baselines.

Usage:
    python -m scripts.compare_rl_capa_vs_baselines \
        --output-dir outputs/plots/rl_capa_compare \
        --num-parcels 100 --courier-speed-kmh 30 --deadline-seconds 900

All RL-CAPA + baseline runners reuse the same Chengdu environment configuration
so the resulting ``comparison.json`` directly answers "did RL-CAPA TR beat the
baselines on this exact scenario?"
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


DEFAULT_BASELINES = ("capa", "greedy", "mra", "basegta", "impgta", "ramcom")


def _run(cmd: list[str]) -> None:
    """Run one CLI command, streaming its output and raising on non-zero exit."""

    print(f"\n$ {' '.join(cmd)}", flush=True)
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        raise SystemExit(f"command failed (exit {result.returncode}): {' '.join(cmd)}")


def _load_summary(path: Path) -> dict:
    """Load and return the JSON summary written by one algorithm runner."""

    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main(argv: list[str] | None = None) -> int:
    """Train RL-CAPA, infer, then run baselines and emit one comparison JSON."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, help="Root directory receiving every per-algorithm output and the final comparison.json.")
    parser.add_argument("--data-dir", default="Data")
    parser.add_argument("--num-parcels", type=int, default=100)
    parser.add_argument("--local-couriers", type=int, default=10)
    parser.add_argument("--platforms", type=int, default=2)
    parser.add_argument("--couriers-per-platform", type=int, default=5)
    parser.add_argument("--task-window-start-seconds", type=float, default=0)
    parser.add_argument("--task-window-end-seconds", type=float, default=30)
    parser.add_argument("--partner-history-task-count-start", type=int, default=200)
    parser.add_argument("--partner-history-task-count-step", type=int, default=0)
    parser.add_argument("--batch-size", type=int, default=15)
    parser.add_argument("--rl-batch-actions", type=int, nargs="+", default=[10, 15, 20])
    parser.add_argument("--step-seconds", type=int, default=60)
    parser.add_argument("--courier-speed-kmh", type=float, default=30.0)
    parser.add_argument("--deadline-seconds", type=int, default=900)
    parser.add_argument("--episodes", type=int, default=500)
    parser.add_argument("--rl-warmup-episodes", type=int, default=20)
    parser.add_argument("--rl-entropy-start", type=float, default=0.05)
    parser.add_argument("--rl-entropy-end", type=float, default=0.001)
    parser.add_argument("--rl-entropy-decay-episodes", type=int, default=250)
    parser.add_argument("--rl-lr-actor", type=float, default=1e-4)
    parser.add_argument("--rl-use-service-slack", action="store_true")
    parser.add_argument("--rl-disable-advantage-normalization", action="store_true", default=True)
    parser.add_argument("--baselines", nargs="+", default=list(DEFAULT_BASELINES))
    parser.add_argument("--skip-train", action="store_true", help="Skip RL-CAPA training (reuse existing checkpoint in <output>/rl-capa/checkpoints).")
    args = parser.parse_args(argv)

    output_root = Path(args.output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    rl_dir = output_root / "rl-capa"
    rl_infer_dir = output_root / "rl-capa-infer"

    shared_env_args = [
        "--data-dir", args.data_dir,
        "--num-parcels", str(args.num_parcels),
        "--local-couriers", str(args.local_couriers),
        "--platforms", str(args.platforms),
        "--couriers-per-platform", str(args.couriers_per_platform),
        "--task-window-start-seconds", str(args.task_window_start_seconds),
        "--task-window-end-seconds", str(args.task_window_end_seconds),
        "--partner-history-task-count-start", str(args.partner_history_task_count_start),
        "--partner-history-task-count-step", str(args.partner_history_task_count_step),
        "--batch-size", str(args.batch_size),
        "--courier-speed-kmh", str(args.courier_speed_kmh),
        "--deadline-seconds", str(args.deadline_seconds),
        "--step-seconds", str(args.step_seconds),
    ]
    rl_train_args = [
        sys.executable, "runner.py", "run",
        "--algorithm", "rl-capa",
        *shared_env_args,
        "--rl-batch-actions", *(str(value) for value in args.rl_batch_actions),
        "--episodes", str(args.episodes),
        "--rl-warmup-episodes", str(args.rl_warmup_episodes),
        "--rl-entropy-start", str(args.rl_entropy_start),
        "--rl-entropy-end", str(args.rl_entropy_end),
        "--rl-entropy-decay-episodes", str(args.rl_entropy_decay_episodes),
        "--rl-lr-actor", str(args.rl_lr_actor),
        "--output-dir", str(rl_dir),
    ]
    if args.rl_disable_advantage_normalization:
        rl_train_args.append("--rl-disable-advantage-normalization")
    if args.rl_use_service_slack:
        rl_train_args.append("--rl-use-service-slack")

    if not args.skip_train:
        _run(rl_train_args)

    rl_infer_args = [
        sys.executable, "runner.py", "run",
        "--algorithm", "rl-capa-infer",
        *shared_env_args,
        "--rl-batch-actions", *(str(value) for value in args.rl_batch_actions),
        "--rl-checkpoint-dir", str(rl_dir / "checkpoints"),
        "--episodes", "0",
        "--output-dir", str(rl_infer_dir),
    ]
    if args.rl_use_service_slack:
        rl_infer_args.append("--rl-use-service-slack")
    _run(rl_infer_args)

    baseline_metrics: dict[str, dict] = {}
    for baseline in args.baselines:
        baseline_dir = output_root / baseline
        baseline_args = [
            sys.executable, "runner.py", "run",
            "--algorithm", baseline,
            *shared_env_args,
            "--output-dir", str(baseline_dir),
        ]
        _run(baseline_args)
        summary_path = baseline_dir / "summary.json"
        if summary_path.exists():
            baseline_metrics[baseline] = _load_summary(summary_path).get("metrics", {})

    rl_infer_summary_path = rl_infer_dir / "summary.json"
    rl_metrics = (
        _load_summary(rl_infer_summary_path).get("metrics", {})
        if rl_infer_summary_path.exists()
        else {}
    )

    comparison = {
        "config": vars(args),
        "rl_capa_infer_metrics": rl_metrics,
        "baseline_metrics": baseline_metrics,
    }
    comparison_path = output_root / "comparison.json"
    with comparison_path.open("w", encoding="utf-8") as handle:
        json.dump(comparison, handle, indent=2)
    print(f"\nwrote comparison: {comparison_path}")
    print("\n=== TR comparison ===")
    print(f"rl-capa-infer: TR={rl_metrics.get('TR', float('nan')):.2f}")
    for name, metrics in baseline_metrics.items():
        print(f"{name:>14s}: TR={metrics.get('TR', float('nan')):.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
