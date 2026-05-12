"""Run Chengdu Exp-7: TR/CR/BPT versus deadline processing delay."""

from __future__ import annotations

from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.deadline_disturbance import DEADLINE_DELAY_AXIS
from experiments.paper_chengdu import (
    build_capa_runner_overrides_from_args,
    build_fixed_config_from_args,
    build_script_parser,
    run_chengdu_paper_experiment,
    run_chengdu_paper_point,
    run_chengdu_paper_split_experiment,
)


DEFAULT_DEADLINE_DISTURBANCE_ALGORITHMS = ("rl-capa-infer", "ramcom")


def main() -> int:
    """Parse CLI args and launch the deadline-delay robustness experiment."""

    parser = build_script_parser("Run Chengdu experiment 7: metrics versus deadline processing delay.")
    parser.set_defaults(algorithms=list(DEFAULT_DEADLINE_DISTURBANCE_ALGORITHMS))
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
    else:
        raise SystemExit(f"Unsupported execution mode for Exp-7: {args.execution_mode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
