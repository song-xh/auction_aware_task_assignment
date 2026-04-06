"""Run the Chengdu paper-style TR/CR/BPT versus courier-capacity experiment."""

from __future__ import annotations

from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.paper_chengdu import build_fixed_config_from_args, build_script_parser, run_chengdu_paper_experiment, run_chengdu_paper_point, run_chengdu_paper_split_experiment


def main() -> int:
    """Parse CLI args and launch the courier-capacity paper experiment."""
    parser = build_script_parser("Run Chengdu supplementary experiment: metrics versus courier capacity.")
    args = parser.parse_args()
    fixed_config = build_fixed_config_from_args(args)
    if args.execution_mode == "direct":
        run_chengdu_paper_experiment(
            axis="courier_capacity",
            output_dir=Path(args.output_dir),
            algorithms=args.algorithms,
            fixed_config_overrides=fixed_config,
            preset_name=args.preset,
            max_workers=args.max_workers,
        )
    elif args.execution_mode == "split":
        run_chengdu_paper_split_experiment(
            axis="courier_capacity",
            script_path=Path(__file__).resolve(),
            tmp_root=Path(args.tmp_root or "/tmp/chengdu_exp6_split"),
            output_dir=Path(args.output_dir),
            algorithms=args.algorithms,
            fixed_config_overrides=fixed_config,
            preset_name=args.preset,
            poll_seconds=args.poll_seconds,
            progress_mode=args.progress_mode,
        )
    elif args.execution_mode == "point":
        if args.point_value is None:
            raise SystemExit("--point-value is required in point mode.")
        run_chengdu_paper_point(
            axis="courier_capacity",
            axis_value=float(args.point_value),
            output_dir=Path(args.output_dir),
            algorithms=args.algorithms,
            fixed_config_overrides=fixed_config,
        )
    else:
        raise SystemExit(f"Unsupported execution mode for Exp-6: {args.execution_mode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
