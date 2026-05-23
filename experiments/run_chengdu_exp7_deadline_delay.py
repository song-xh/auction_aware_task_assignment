"""Run Chengdu Exp-7: TR/CR/BPT versus deadline processing delay."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.deadline_disturbance import DEADLINE_DELAY_AXIS
from experiments.exp7_robustness import DelaySpec, run_exp7_robustness
from experiments.paper_chengdu import (
    build_capa_runner_overrides_from_args,
    build_fixed_config_from_args,
    build_script_parser,
    run_chengdu_paper_experiment,
    run_chengdu_paper_point,
    run_chengdu_paper_split_experiment,
)


DEFAULT_DEADLINE_DISTURBANCE_ALGORITHMS = ("rl-capa", "ramcom")
DEFAULT_ROBUSTNESS_ALGORITHMS = ("capa", "rl-capa-infer")


def _add_robustness_arguments(parser: argparse.ArgumentParser) -> None:
    """Register the robustness-mode CLI surface (delay-seconds + delay-window)."""

    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=None,
        help="Robustness mode: delay duration in seconds applied to parcels inside --delay-window.",
    )
    parser.add_argument(
        "--delay-window",
        type=str,
        default=None,
        help='Robustness mode: inclusive "start,end" true-arrival window receiving the delay.',
    )
    parser.add_argument(
        "--rl-use-service-slack",
        action="store_true",
        help="Robustness mode: match checkpoint trained with --rl-use-service-slack so the Stage-2 dim aligns.",
    )


def main() -> int:
    """Parse CLI args and launch the deadline-delay robustness experiment."""

    parser = build_script_parser("Run Chengdu experiment 7: metrics versus deadline processing delay.")
    parser.set_defaults(algorithms=list(DEFAULT_DEADLINE_DISTURBANCE_ALGORITHMS))
    _add_robustness_arguments(parser)
    args = parser.parse_args()
    fixed_config = build_fixed_config_from_args(args)
    runner_overrides = build_capa_runner_overrides_from_args(args)
    if args.execution_mode == "direct":
        run_chengdu_paper_experiment(
            axis=DEADLINE_DELAY_AXIS,
            output_dir=Path(args.output_dir),
            algorithms=args.algorithms,
            fixed_config_overrides=fixed_config,
            preset_name=args.preset,
            max_workers=args.max_workers,
        )
    elif args.execution_mode == "split":
        run_chengdu_paper_split_experiment(
            axis=DEADLINE_DELAY_AXIS,
            script_path=Path(__file__).resolve(),
            tmp_root=Path(args.tmp_root or "/tmp/chengdu_exp7_deadline_delay_split"),
            output_dir=Path(args.output_dir),
            algorithms=args.algorithms,
            fixed_config_overrides=fixed_config,
            preset_name=args.preset,
            poll_seconds=args.poll_seconds,
            progress_mode=args.progress_mode,
            seed_path=Path(args.seed_path) if args.seed_path else None,
            runner_overrides_by_algorithm=runner_overrides,
        )
    elif args.execution_mode == "point":
        if args.point_value is None:
            raise SystemExit("--point-value is required in point mode.")
        run_chengdu_paper_point(
            axis=DEADLINE_DELAY_AXIS,
            axis_value=float(args.point_value),
            output_dir=Path(args.output_dir),
            algorithms=args.algorithms,
            fixed_config_overrides=fixed_config,
            seed_path=Path(args.seed_path) if args.seed_path else None,
            runner_overrides_by_algorithm=runner_overrides,
        )
    elif args.execution_mode == "robustness":
        _run_robustness_mode(args=args, fixed_config=fixed_config)
    else:
        raise SystemExit(f"Unsupported execution mode for Exp-7: {args.execution_mode}")
    return 0


def _run_robustness_mode(args: argparse.Namespace, fixed_config: dict[str, Any]) -> None:
    """Build a canonical environment and run the baseline vs delayed comparison."""

    if args.delay_seconds is None or args.delay_window is None:
        raise SystemExit("robustness mode requires both --delay-seconds and --delay-window.")
    if "rl-capa-infer" in (args.algorithms or DEFAULT_ROBUSTNESS_ALGORITHMS) and not args.rl_checkpoint_dir:
        raise SystemExit("rl-capa-infer requires --rl-checkpoint-dir to load weights.")
    algorithms = list(args.algorithms or DEFAULT_ROBUSTNESS_ALGORITHMS)
    delay_spec = DelaySpec.from_cli(
        delay_seconds=args.delay_seconds,
        delay_window=args.delay_window,
    )
    canonical_environment = _build_canonical_environment(fixed_config)
    runner_kwargs = {
        algorithm: _runner_kwargs_for(algorithm, args, fixed_config)
        for algorithm in algorithms
    }
    run_exp7_robustness(
        canonical_environment=canonical_environment,
        delay_spec=delay_spec,
        algorithms=algorithms,
        output_dir=Path(args.output_dir),
        runner_kwargs_by_algorithm=runner_kwargs,
    )


def _build_canonical_environment(fixed_config: dict[str, Any]) -> Any:
    """Materialize a Chengdu environment from the resolved fixed-config dict."""

    from env.chengdu import ChengduEnvironment

    return ChengduEnvironment.build(
        data_dir=Path(fixed_config.get("data_dir", "Data")),
        num_parcels=int(fixed_config.get("num_parcels", 100)),
        local_courier_count=int(fixed_config.get("local_couriers", 10)),
        cooperating_platform_count=int(fixed_config.get("platforms", 2)),
        couriers_per_platform=int(fixed_config.get("couriers_per_platform", 5)),
        service_radius_km=fixed_config.get("service_radius_km"),
        courier_capacity=fixed_config.get("courier_capacity"),
        task_window_start_seconds=fixed_config.get("task_window_start_seconds"),
        task_window_end_seconds=fixed_config.get("task_window_end_seconds"),
        task_sampling_seed=int(fixed_config.get("task_sampling_seed", 1)),
        partner_history_task_count_start=int(fixed_config.get("partner_history_task_count_start", 25_000)),
        partner_history_task_count_step=int(fixed_config.get("partner_history_task_count_step", 2_500)),
        deadline_seconds=fixed_config.get("deadline_seconds"),
        courier_speed_kmh=fixed_config.get("courier_speed_kmh"),
    )


def _runner_kwargs_for(
    algorithm: str,
    args: argparse.Namespace,
    fixed_config: dict[str, Any],
) -> dict[str, Any]:
    """Build per-algorithm runner kwargs for the robustness comparison."""

    if algorithm == "capa":
        return {"batch_size": int(fixed_config.get("batch_size", 30))}
    if algorithm == "rl-capa-infer":
        return {
            "checkpoint_dir": args.rl_checkpoint_dir,
            "min_batch_size": int(fixed_config.get("rl_min_batch_size", 10)),
            "max_batch_size": int(fixed_config.get("rl_max_batch_size", 20)),
            "batch_actions": fixed_config.get("rl_batch_actions"),
            "step_seconds": int(fixed_config.get("rl_step_seconds", 60)),
            "use_service_slack": bool(getattr(args, "rl_use_service_slack", False)),
        }
    return {}


if __name__ == "__main__":
    raise SystemExit(main())
