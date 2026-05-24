"""Run fixed-data Chengdu Exp-7 delay comparisons for CAPA, ImpGTA, and RamCOM."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.exp7_fixed_delay_compare import (
    DEFAULT_FIXED_DELAY_VALUES,
    run_exp7_fixed_delay_compare,
)
from experiments.paper_chengdu import (
    build_capa_runner_overrides_from_args,
    build_fixed_config_from_args,
    build_script_parser,
)
from experiments.run_chengdu_exp7_deadline_delay import _build_canonical_environment


DEFAULT_FIXED_COMPARE_ALGORITHMS = ("capa", "impgta", "ramcom")


def _add_fixed_compare_arguments(parser: argparse.ArgumentParser) -> None:
    """Register the fixed-delay comparison CLI surface."""

    parser.add_argument(
        "--delay-window",
        type=str,
        required=True,
        help='Inclusive "start,end" true-arrival window receiving the delay.',
    )
    parser.add_argument(
        "--delay-values",
        type=float,
        nargs="+",
        default=list(DEFAULT_FIXED_DELAY_VALUES),
        help="Ordered delay values in seconds. Default: 5 10 20 30 60.",
    )
    parser.add_argument(
        "--data-cache-dir",
        type=Path,
        default=Path("Data/delay"),
        help="Directory receiving canonical/delayed CSV exports plus the replay seed.",
    )
    parser.add_argument(
        "--data-mode",
        choices=("auto", "reuse", "regenerate"),
        default="auto",
        help="Dataset cache mode: reuse existing exported Data/delay assets, regenerate them, or auto-reuse when present.",
    )


def main() -> int:
    """Parse CLI args and launch the fixed-data Exp-7 delay comparison."""

    parser = build_script_parser(
        "Run Chengdu Exp-7 with fixed canonical data and per-delay comparisons for CAPA, ImpGTA, and RamCOM."
    )
    parser.set_defaults(algorithms=list(DEFAULT_FIXED_COMPARE_ALGORITHMS))
    _add_fixed_compare_arguments(parser)
    args = parser.parse_args()
    fixed_config = build_fixed_config_from_args(args)
    capa_overrides = build_capa_runner_overrides_from_args(args)
    canonical_environment = _build_canonical_environment(fixed_config)
    delay_window = _parse_delay_window(args.delay_window)
    runner_kwargs = {
        "capa": {
            "batch_size": int(fixed_config.get("batch_size", 30)),
            **capa_overrides.get("capa", {}),
        },
        "impgta": {
            "batch_size": int(fixed_config.get("batch_size", 30)),
        },
        "ramcom": {
            "batch_size": int(fixed_config.get("batch_size", 30)),
        },
    }
    run_exp7_fixed_delay_compare(
        canonical_environment=canonical_environment,
        delay_values=list(args.delay_values),
        delay_window=delay_window,
        algorithms=list(args.algorithms or DEFAULT_FIXED_COMPARE_ALGORITHMS),
        output_dir=Path(args.output_dir),
        data_cache_dir=Path(args.data_cache_dir),
        data_mode=str(args.data_mode),
        runner_kwargs_by_algorithm=runner_kwargs,
    )
    return 0


def _parse_delay_window(spec: str) -> tuple[float, float]:
    """Parse one fixed-delay comparison window from CLI text."""

    from experiments.deadline_disturbance import parse_delay_window

    return parse_delay_window(spec)


if __name__ == "__main__":
    raise SystemExit(main())
