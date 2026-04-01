"""Run the Chengdu paper-style TR/CR/BPT versus cooperating-platform-count experiment."""

from __future__ import annotations

from pathlib import Path

from experiments.paper_chengdu import build_fixed_config_from_args, build_script_parser, run_chengdu_paper_experiment


def main() -> int:
    """Parse CLI args and launch the platform-count paper experiment."""
    parser = build_script_parser("Run Chengdu paper experiment 4: metrics versus platform count.")
    args = parser.parse_args()
    run_chengdu_paper_experiment(
        axis="platforms",
        output_dir=Path(args.output_dir),
        algorithms=args.algorithms,
        fixed_config_overrides=build_fixed_config_from_args(args),
        preset_name=args.preset,
        max_workers=args.max_workers,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
