"""Run the Chengdu paper-style default-setting comparison experiment."""

from __future__ import annotations

from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.paper_chengdu import build_fixed_config_from_args, build_script_parser, run_chengdu_default_comparison


def main() -> int:
    """Parse CLI args and launch the default-setting multi-algorithm comparison."""
    parser = build_script_parser("Run Chengdu paper experiment 5: default-setting multi-algorithm comparison.")
    args = parser.parse_args()
    if args.execution_mode != "direct":
        raise SystemExit("Exp-5 default comparison only supports --execution-mode direct.")
    run_chengdu_default_comparison(
        output_dir=Path(args.output_dir),
        algorithms=args.algorithms,
        fixed_config_overrides=build_fixed_config_from_args(args),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
