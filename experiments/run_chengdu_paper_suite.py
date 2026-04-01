"""Run all Chengdu paper-style experiments."""

from __future__ import annotations

from pathlib import Path

from experiments.paper_chengdu import build_fixed_config_from_args, build_script_parser, run_chengdu_paper_suite


def main() -> int:
    """Parse CLI args and launch the full Chengdu paper suite."""
    parser = build_script_parser("Run the full Chengdu paper-style experiment suite.")
    args = parser.parse_args()
    run_chengdu_paper_suite(
        output_dir=Path(args.output_dir),
        algorithms=args.algorithms,
        fixed_config_overrides=build_fixed_config_from_args(args),
        preset_name=args.preset,
        max_workers=args.max_workers,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
