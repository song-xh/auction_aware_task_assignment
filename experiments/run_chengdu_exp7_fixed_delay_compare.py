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
    run_exp7_fixed_delay_direct,
    run_exp7_fixed_delay_point,
    run_exp7_fixed_delay_split_experiment,
)
from experiments.paper_chengdu import PAPER_EXECUTION_MODES
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
    algorithms = list(args.algorithms or DEFAULT_FIXED_COMPARE_ALGORITHMS)
    if args.execution_mode == "direct":
        canonical_environment = _build_canonical_environment(fixed_config)
        run_exp7_fixed_delay_direct(
            canonical_environment=canonical_environment,
            delay_values=list(args.delay_values),
            delay_window=delay_window,
            algorithms=algorithms,
            output_dir=Path(args.output_dir),
            data_cache_dir=Path(args.data_cache_dir),
            data_mode=str(args.data_mode),
            runner_kwargs_by_algorithm=runner_kwargs,
            max_workers=args.max_workers,
        )
    elif args.execution_mode == "point":
        if args.point_value is None:
            raise SystemExit("--point-value is required in point mode.")
        if not args.seed_path:
            raise SystemExit("--seed-path is required in point mode.")
        run_exp7_fixed_delay_point(
            seed_path=Path(args.seed_path),
            delay_seconds=float(args.point_value),
            delay_window=delay_window,
            output_dir=Path(args.output_dir),
            algorithms=algorithms,
            batch_size=int(fixed_config.get("batch_size", 30)),
            runner_kwargs_by_algorithm=runner_kwargs,
        )
    elif args.execution_mode == "split":
        canonical_environment = _build_canonical_environment(fixed_config)
        run_exp7_fixed_delay_split_experiment(
            script_path=Path(__file__).resolve(),
            canonical_environment=canonical_environment,
            delay_values=list(args.delay_values),
            delay_window=delay_window,
            algorithms=algorithms,
            output_dir=Path(args.output_dir),
            data_cache_dir=Path(args.data_cache_dir),
            tmp_root=Path(args.tmp_root or "/tmp/chengdu_exp7_fixed_delay_split"),
            batch_size=int(fixed_config.get("batch_size", 30)),
            data_mode=str(args.data_mode),
            poll_seconds=args.poll_seconds,
            progress_mode=str(args.progress_mode),
            runner_kwargs_by_algorithm=runner_kwargs,
            fixed_config=fixed_config,
        )
    else:
        raise SystemExit(
            f"Unsupported execution mode for fixed Exp-7: {args.execution_mode}. "
            f"Supported: {', '.join(mode for mode in PAPER_EXECUTION_MODES if mode in {'direct', 'point', 'split'})}."
        )
    return 0


def _parse_delay_window(spec: str) -> tuple[float, float]:
    """Parse one fixed-delay comparison window from CLI text."""

    from experiments.deadline_disturbance import parse_delay_window

    return parse_delay_window(spec)


if __name__ == "__main__":
    raise SystemExit(main())
