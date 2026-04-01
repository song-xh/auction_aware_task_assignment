"""Helpers and defaults for Chengdu-backed paper-style experiment scripts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

from algorithms.registry import build_algorithm_runner
from env.chengdu import ChengduEnvironment
from .compare import run_comparison_sweep
from .paper_config import DEFAULT_CHENGDU_PAPER_ALGORITHMS, PAPER_SUITE_PRESETS
from .plotting import save_default_comparison_plots
from .suites import run_experiment_suite


DEFAULT_CHENGDU_PAPER_FIXED_CONFIG: dict[str, Any] = {
    "data_dir": Path("Data"),
    "num_parcels": 3000,
    "local_couriers": 200,
    "platforms": 4,
    "couriers_per_platform": 50,
    "courier_capacity": 50.0,
    "service_radius_km": 1.0,
    "batch_size": 300,
    "prediction_window_seconds": 180,
}


def run_chengdu_paper_experiment(
    axis: str,
    output_dir: Path,
    algorithms: Sequence[str] = DEFAULT_CHENGDU_PAPER_ALGORITHMS,
    fixed_config_overrides: dict[str, Any] | None = None,
    preset_name: str = "formal",
    max_workers: int | None = None,
) -> dict[str, Any]:
    """Run one Chengdu paper-style comparison sweep and persist a manifest."""
    fixed_config = dict(DEFAULT_CHENGDU_PAPER_FIXED_CONFIG)
    if fixed_config_overrides:
        fixed_config.update(fixed_config_overrides)
    values = PAPER_SUITE_PRESETS["chengdu-paper"][preset_name][axis]
    summary = run_comparison_sweep(
        algorithms=algorithms,
        output_dir=output_dir,
        sweep_parameter=axis,
        sweep_values=values,
        fixed_config=fixed_config,
        max_workers=max_workers,
    )
    manifest = {
        "axis": axis,
        "preset": preset_name,
        "algorithms": list(algorithms),
        "plots": {
            "TR": str(output_dir / f"tr_vs_{axis}.png"),
            "CR": str(output_dir / f"cr_vs_{axis}.png"),
            "BPT": str(output_dir / f"bpt_vs_{axis}.png"),
        },
        "summary": str(output_dir / "summary.json"),
    }
    with (output_dir / "paper_manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
    return summary


def run_chengdu_paper_suite(
    output_dir: Path,
    algorithms: Sequence[str] = DEFAULT_CHENGDU_PAPER_ALGORITHMS,
    fixed_config_overrides: dict[str, Any] | None = None,
    preset_name: str = "formal",
    max_workers: int | None = None,
) -> dict[str, Any]:
    """Run all supported Chengdu paper-style sweeps and persist a suite manifest."""
    fixed_config = dict(DEFAULT_CHENGDU_PAPER_FIXED_CONFIG)
    if fixed_config_overrides:
        fixed_config.update(fixed_config_overrides)
    return run_experiment_suite(
        suite_name="chengdu-paper",
        preset_name=preset_name,
        algorithms=algorithms,
        output_dir=output_dir,
        fixed_config=fixed_config,
        max_workers=max_workers,
    )


def run_chengdu_default_comparison(
    output_dir: Path,
    algorithms: Sequence[str] = DEFAULT_CHENGDU_PAPER_ALGORITHMS,
    fixed_config_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run one default-setting Chengdu comparison and render categorical comparison plots."""
    fixed_config = dict(DEFAULT_CHENGDU_PAPER_FIXED_CONFIG)
    if fixed_config_overrides:
        fixed_config.update(fixed_config_overrides)
    environment = ChengduEnvironment.build(
        data_dir=Path(fixed_config["data_dir"]),
        num_parcels=int(fixed_config["num_parcels"]),
        local_courier_count=int(fixed_config["local_couriers"]),
        cooperating_platform_count=int(fixed_config["platforms"]),
        couriers_per_platform=int(fixed_config["couriers_per_platform"]),
        service_radius_km=fixed_config["service_radius_km"],
        courier_capacity=fixed_config["courier_capacity"],
    )
    from .seeding import build_environment_seed, clone_environment_from_seed

    seed = build_environment_seed(environment)
    output_dir.mkdir(parents=True, exist_ok=True)
    summaries: dict[str, Any] = {}
    for algorithm in algorithms:
        runner_kwargs = {"batch_size": int(fixed_config["batch_size"])} if algorithm in {"capa", "greedy", "mra"} else {}
        if algorithm == "impgta":
            runner_kwargs = {"prediction_window_seconds": int(fixed_config["prediction_window_seconds"])}
        runner = build_algorithm_runner(algorithm, **runner_kwargs)
        summaries[algorithm] = runner.run(
            environment=clone_environment_from_seed(seed),
            output_dir=output_dir / algorithm,
        )

    summary = {
        "algorithms": list(algorithms),
        "fixed_config": {
            key: str(value) if isinstance(value, Path) else value for key, value in fixed_config.items()
        },
        "results": summaries,
    }
    with (output_dir / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)

    save_default_comparison_plots(summary=summary, output_dir=output_dir)
    return summary


def build_script_parser(description: str) -> argparse.ArgumentParser:
    """Build a shared CLI parser for Chengdu paper-style experiment scripts."""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--data-dir", default="Data", help="Path to the Chengdu data directory.")
    parser.add_argument("--output-dir", required=True, help="Directory for plots and summary files.")
    parser.add_argument("--preset", default="formal", choices=tuple(PAPER_SUITE_PRESETS["chengdu-paper"].keys()), help="Paper preset to execute.")
    parser.add_argument(
        "--algorithms",
        nargs="+",
        default=list(DEFAULT_CHENGDU_PAPER_ALGORITHMS),
        help="Algorithms included in the experiment or comparison.",
    )
    parser.add_argument("--max-workers", type=int, default=None, help="Optional process count for parallel sweep-point execution.")
    parser.add_argument("--num-parcels", type=int, default=DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["num_parcels"])
    parser.add_argument("--local-couriers", type=int, default=DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["local_couriers"])
    parser.add_argument("--platforms", type=int, default=DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["platforms"])
    parser.add_argument("--couriers-per-platform", type=int, default=DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["couriers_per_platform"])
    parser.add_argument("--courier-capacity", type=float, default=DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["courier_capacity"])
    parser.add_argument("--service-radius-km", type=float, default=DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["service_radius_km"])
    parser.add_argument("--batch-size", type=int, default=DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["batch_size"])
    return parser


def build_fixed_config_from_args(args: argparse.Namespace) -> dict[str, Any]:
    """Translate shared script CLI arguments into a fixed Chengdu experiment config."""
    return {
        "data_dir": Path(args.data_dir),
        "num_parcels": args.num_parcels,
        "local_couriers": args.local_couriers,
        "platforms": args.platforms,
        "couriers_per_platform": args.couriers_per_platform,
        "courier_capacity": args.courier_capacity,
        "service_radius_km": args.service_radius_km,
        "batch_size": args.batch_size,
        "prediction_window_seconds": 180,
    }
