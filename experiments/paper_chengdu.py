"""Helpers and defaults for Chengdu-backed paper-style experiment scripts."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import asdict, dataclass
from functools import partial
from statistics import mean
from pathlib import Path
from typing import Any, Sequence

from algorithms.registry import build_algorithm_runner
from capa.config import (
    DEFAULT_CAPA_BATCH_SIZE,
    DEFAULT_COURIER_ALPHA,
    DEFAULT_COURIER_SERVICE_SCORE,
    DEFAULT_DETOUR_FAVORING_CAPA_RUNNER_KWARGS,
    DEFAULT_IMPGTA_PREDICTION_SAMPLING_SEED,
    DEFAULT_IMPGTA_PREDICTION_SUCCESS_RATE,
    DEFAULT_IMPGTA_WINDOW_SECONDS,
    DEFAULT_LOWER_THRESHOLD_CAPA_RUNNER_KWARGS,
    DEFAULT_PAPER_CAPA_RUNNER_KWARGS,
    DEFAULT_PLATFORM_QUALITY_START,
    DEFAULT_PLATFORM_QUALITY_STEP,
)
from env.chengdu import ChengduEnvironment
from experiments.config import ExperimentConfig, apply_sweep_axis
from experiments.framework import ExperimentPointSpec, ExperimentSplitSpec, ManagedRoundSpec, run_environment_comparison_point, run_managed_rounds, run_seeded_comparison_point, run_seeded_split_experiment
from experiments.progress import build_point_progress_snapshot, write_point_progress
from .compare import run_comparison_sweep
from .paper_config import DEFAULT_CHENGDU_PAPER_ALGORITHMS, PAPER_SUITE_PRESETS
from .plotting import save_default_comparison_plots
from .progress import ProgressMode
from .seeding import build_environment_seed, clone_environment_from_seed, derive_environment_for_axis, save_environment_seed
from .suites import run_experiment_suite


DEFAULT_CHENGDU_PAPER_FIXED_CONFIG: dict[str, Any] = {
    "data_dir": Path("Data"),
    "num_parcels": 5000,
    "local_couriers": 200,
    "platforms": 4,
    "couriers_per_platform": 50,
    "courier_capacity": 50.0,
    "service_radius_km": 1.0,
    "batch_size": DEFAULT_CAPA_BATCH_SIZE,
    "prediction_window_seconds": DEFAULT_IMPGTA_WINDOW_SECONDS,
    "prediction_success_rate": DEFAULT_IMPGTA_PREDICTION_SUCCESS_RATE,
    "prediction_sampling_seed": DEFAULT_IMPGTA_PREDICTION_SAMPLING_SEED,
    "task_window_start_seconds": None,
    "task_window_end_seconds": None,
    "task_sampling_seed": 1,
    "partner_history_task_count_start": 25_000,
    "partner_history_task_count_step": 2_500,
    "courier_alpha": DEFAULT_COURIER_ALPHA,
    "courier_beta": None,
    "courier_service_score": DEFAULT_COURIER_SERVICE_SCORE,
    "platform_quality_start": DEFAULT_PLATFORM_QUALITY_START,
    "platform_quality_step": DEFAULT_PLATFORM_QUALITY_STEP,
    "rl_future_feature_window_seconds": 300,
}


@dataclass(frozen=True)
class Exp1RoundSpec:
    """Define one CAPA parameterization candidate for managed Exp-1 runs."""

    name: str
    rationale: str
    capa_runner_kwargs: dict[str, float]


DEFAULT_EXP1_ROUNDS: tuple[Exp1RoundSpec, ...] = (
    Exp1RoundSpec(
        name="paper-default",
        rationale="Paper-default CAPA parameters.",
        capa_runner_kwargs=dict(DEFAULT_PAPER_CAPA_RUNNER_KWARGS),
    ),
    Exp1RoundSpec(
        name="lower-threshold",
        rationale="Lower Eq.7 threshold to keep more feasible parcels in local matching when CR lags.",
        capa_runner_kwargs=dict(DEFAULT_LOWER_THRESHOLD_CAPA_RUNNER_KWARGS),
    ),
    Exp1RoundSpec(
        name="detour-favoring",
        rationale="Favor detour efficiency while keeping the lower threshold when TR still lags.",
        capa_runner_kwargs=dict(DEFAULT_DETOUR_FAVORING_CAPA_RUNNER_KWARGS),
    ),
)


PAPER_EXECUTION_MODES = ("direct", "split", "point", "managed")


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


def run_chengdu_paper_point(
    axis: str,
    axis_value: int | float,
    output_dir: Path,
    algorithms: Sequence[str] = DEFAULT_CHENGDU_PAPER_ALGORITHMS,
    fixed_config_overrides: dict[str, Any] | None = None,
    seed_path: Path | None = None,
    runner_overrides_by_algorithm: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run one Chengdu paper comparison point and persist a point-level summary.

    Args:
        axis: Sweep axis name.
        axis_value: Concrete point value on the axis.
        output_dir: Point output directory.
        algorithms: Algorithms evaluated at this point.
        fixed_config_overrides: Base fixed Chengdu configuration.
        seed_path: Optional canonical seed path reused across split points.
        runner_overrides_by_algorithm: Optional per-algorithm runner overrides.

    Returns:
        One normalized point summary keyed by algorithm.
    """

    fixed_config = dict(DEFAULT_CHENGDU_PAPER_FIXED_CONFIG)
    if fixed_config_overrides:
        fixed_config.update(fixed_config_overrides)
    merged_runner_overrides = build_paper_runner_overrides_from_fixed_config(
        fixed_config=fixed_config,
        explicit_overrides=runner_overrides_by_algorithm,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_point_bootstrap_progress(
        output_dir=output_dir,
        axis=axis,
        axis_value=axis_value,
        total_algorithms=len(algorithms),
        detail=f"building environment for {axis}={axis_value}",
    )
    if seed_path is not None:
        point_spec = ExperimentPointSpec(
            axis_name=axis,
            axis_value=axis_value,
            output_dir=output_dir,
            algorithms=algorithms,
            batch_size=int(fixed_config["batch_size"]),
            runner_overrides_by_algorithm=merged_runner_overrides,
        )
        return run_seeded_comparison_point(
            seed_path=seed_path,
            point_spec=point_spec,
            environment_deriver=lambda seed, value: derive_environment_for_axis(seed, axis, value),
            runner_builder=partial(_build_paper_runner, runner_overrides_by_algorithm=merged_runner_overrides),
        )
    point_config = apply_sweep_axis(
        ExperimentConfig(
            data_dir=Path(fixed_config["data_dir"]),
            num_parcels=int(fixed_config["num_parcels"]),
            local_couriers=int(fixed_config["local_couriers"]),
            platforms=int(fixed_config["platforms"]),
            couriers_per_platform=int(fixed_config["couriers_per_platform"]),
            batch_size=int(fixed_config["batch_size"]),
            prediction_window_seconds=int(fixed_config["prediction_window_seconds"]),
            prediction_success_rate=float(fixed_config["prediction_success_rate"]),
            prediction_sampling_seed=int(fixed_config["prediction_sampling_seed"]),
            service_radius_km=float(fixed_config["service_radius_km"]) if fixed_config["service_radius_km"] is not None else None,
            courier_capacity=float(fixed_config["courier_capacity"]) if fixed_config["courier_capacity"] is not None else None,
            task_window_start_seconds=float(fixed_config["task_window_start_seconds"]) if fixed_config["task_window_start_seconds"] is not None else None,
            task_window_end_seconds=float(fixed_config["task_window_end_seconds"]) if fixed_config["task_window_end_seconds"] is not None else None,
            task_sampling_seed=int(fixed_config["task_sampling_seed"]),
            partner_history_task_count_start=int(fixed_config["partner_history_task_count_start"]),
            partner_history_task_count_step=int(fixed_config["partner_history_task_count_step"]),
            courier_alpha=float(fixed_config["courier_alpha"]),
            courier_beta=float(fixed_config["courier_beta"]) if fixed_config["courier_beta"] is not None else None,
            courier_service_score=float(fixed_config["courier_service_score"]),
            platform_quality_start=float(fixed_config["platform_quality_start"]),
            platform_quality_step=float(fixed_config["platform_quality_step"]),
        ),
        axis,
        axis_value,
    )
    environment = ChengduEnvironment.build(**point_config.as_environment_kwargs())
    point_spec = ExperimentPointSpec(
        axis_name=axis,
        axis_value=axis_value,
        output_dir=output_dir,
        algorithms=algorithms,
        batch_size=int(fixed_config["batch_size"]),
        runner_overrides_by_algorithm=merged_runner_overrides,
    )
    return run_environment_comparison_point(
        environment=environment,
        point_spec=point_spec,
        runner_builder=partial(_build_paper_runner, runner_overrides_by_algorithm=merged_runner_overrides),
    )


def run_chengdu_paper_split_experiment(
    axis: str,
    script_path: Path,
    tmp_root: Path,
    output_dir: Path,
    algorithms: Sequence[str] = DEFAULT_CHENGDU_PAPER_ALGORITHMS,
    fixed_config_overrides: dict[str, Any] | None = None,
    preset_name: str = "formal",
    poll_seconds: int = 30,
    progress_mode: ProgressMode = "overwrite",
    seed_path: Path | None = None,
    runner_overrides_by_algorithm: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run one paper sweep as independent point subprocesses with live progress.

    Args:
        axis: Sweep axis name.
        script_path: Formal script path used for point subprocesses.
        tmp_root: Temporary split root.
        output_dir: Aggregate output directory.
        algorithms: Algorithms evaluated at each point.
        fixed_config_overrides: Base fixed Chengdu configuration.
        preset_name: Preset name controlling sweep values.
        poll_seconds: Poll interval for point subprocesses.
        progress_mode: Terminal progress rendering mode.
        seed_path: Optional canonical seed path reused across split points.
        runner_overrides_by_algorithm: Optional per-algorithm runner overrides.

    Returns:
        Aggregate sweep summary.
    """

    fixed_config = dict(DEFAULT_CHENGDU_PAPER_FIXED_CONFIG)
    if fixed_config_overrides:
        fixed_config.update(fixed_config_overrides)
    merged_runner_overrides = build_paper_runner_overrides_from_fixed_config(
        fixed_config=fixed_config,
        explicit_overrides=runner_overrides_by_algorithm,
    )
    axis_values = PAPER_SUITE_PRESETS["chengdu-paper"][preset_name][axis]
    if seed_path is None:
        canonical_environment = ChengduEnvironment.build(
            **_canonical_environment_kwargs_for_axis(
                axis=axis,
                axis_values=axis_values,
                fixed_config=fixed_config,
            )
        )
        seed_path = tmp_root / "canonical_seed.pkl"
        save_environment_seed(build_environment_seed(canonical_environment), seed_path)
    split_spec = ExperimentSplitSpec(
        experiment_label=_experiment_label_for_axis(axis),
        axis_name=axis,
        axis_values=tuple(axis_values),
        tmp_root=tmp_root,
        output_dir=output_dir,
        algorithms=algorithms,
        batch_size=int(fixed_config["batch_size"]),
        poll_seconds=poll_seconds,
        progress_mode=progress_mode,
        runner_overrides_by_algorithm=merged_runner_overrides,
    )

    def point_command_builder(value: int | float, point_output_dir: Path) -> Sequence[str]:
        """Build one point subprocess command routed back to the formal script."""

        command: list[str] = [
            sys.executable,
            "-u",
            str(script_path),
            "--execution-mode",
            "point",
            "--point-value",
            str(value),
            "--output-dir",
            str(point_output_dir),
            "--algorithms",
            *list(algorithms),
            "--data-dir",
            str(fixed_config["data_dir"]),
            "--local-couriers",
            str(fixed_config["local_couriers"]),
            "--platforms",
            str(fixed_config["platforms"]),
            "--couriers-per-platform",
            str(fixed_config["couriers_per_platform"]),
            "--courier-capacity",
            str(fixed_config["courier_capacity"]),
            "--service-radius-km",
            str(fixed_config["service_radius_km"]),
            "--batch-size",
            str(fixed_config["batch_size"]),
            "--prediction-window-seconds",
            str(fixed_config["prediction_window_seconds"]),
            "--prediction-success-rate",
            str(fixed_config["prediction_success_rate"]),
            "--prediction-sampling-seed",
            str(fixed_config["prediction_sampling_seed"]),
            "--task-sampling-seed",
            str(fixed_config["task_sampling_seed"]),
            "--partner-history-task-count-start",
            str(fixed_config["partner_history_task_count_start"]),
            "--partner-history-task-count-step",
            str(fixed_config["partner_history_task_count_step"]),
            "--courier-alpha",
            str(fixed_config["courier_alpha"]),
            "--courier-service-score",
            str(fixed_config["courier_service_score"]),
            "--platform-quality-start",
            str(fixed_config["platform_quality_start"]),
            "--platform-quality-step",
            str(fixed_config["platform_quality_step"]),
            "--rl-future-feature-window-seconds",
            str(fixed_config["rl_future_feature_window_seconds"]),
        ]
        if fixed_config["courier_beta"] is not None:
            command.extend(["--courier-beta", str(fixed_config["courier_beta"])])
        if fixed_config["task_window_start_seconds"] is not None:
            command.extend(["--task-window-start-seconds", str(fixed_config["task_window_start_seconds"])])
        if fixed_config["task_window_end_seconds"] is not None:
            command.extend(["--task-window-end-seconds", str(fixed_config["task_window_end_seconds"])])
        if seed_path is not None:
            command.extend(["--seed-path", str(seed_path)])
        for algorithm, overrides in merged_runner_overrides.items():
            if algorithm != "capa":
                continue
            command.extend(_build_capa_override_cli_args(overrides))
        return command

    def aggregate_summary_builder(point_output_dirs: dict[int | float, Path]) -> dict[str, Any]:
        """Aggregate finished point summaries into one paper sweep summary."""

        runs = []
        for value in sorted(point_output_dirs):
            with (point_output_dirs[value] / "summary.json").open("r", encoding="utf-8") as handle:
                runs.append(json.load(handle))
        summary = {
            "sweep_parameter": axis,
            "algorithms": list(algorithms),
            "runs": runs,
        }
        output_dir.mkdir(parents=True, exist_ok=True)
        with (output_dir / "summary.json").open("w", encoding="utf-8") as handle:
            json.dump(summary, handle, indent=2)
        from .plotting import save_comparison_plots

        save_comparison_plots(summary=summary, output_dir=output_dir)
        with (output_dir / "paper_manifest.json").open("w", encoding="utf-8") as handle:
            json.dump(
                {
                    "axis": axis,
                    "preset": preset_name,
                    "algorithms": list(algorithms),
                    "summary": str(output_dir / "summary.json"),
                    "tmp_root": str(tmp_root),
                    "seed_path": None if seed_path is None else str(seed_path),
                    "execution_mode": "split",
                },
                handle,
                indent=2,
            )
        return summary

    return run_seeded_split_experiment(
        split_spec=split_spec,
        point_command_builder=point_command_builder,
        aggregate_summary_builder=aggregate_summary_builder,
    )


def analyze_exp1_summary(
    summary: dict[str, Any],
    algorithms: Sequence[str],
    round_spec: Exp1RoundSpec,
    success_tr_ratio: float,
    success_cr_gap: float,
) -> dict[str, Any]:
    """Score one Exp-1 managed round and decide whether CAPA is competitive enough."""

    runs = summary["runs"]
    capa_tr_values = [float(run["capa"]["metrics"]["TR"]) for run in runs]
    capa_cr_values = [float(run["capa"]["metrics"]["CR"]) for run in runs]
    capa_bpt_values = [float(run["capa"]["metrics"]["BPT"]) for run in runs]
    baseline_algorithms = [name for name in algorithms if name != "capa"]
    baseline_scores: dict[str, dict[str, float]] = {}
    for algorithm in baseline_algorithms:
        baseline_scores[algorithm] = {
            "avg_TR": mean(float(run[algorithm]["metrics"]["TR"]) for run in runs),
            "avg_CR": mean(float(run[algorithm]["metrics"]["CR"]) for run in runs),
            "avg_BPT": mean(float(run[algorithm]["metrics"]["BPT"]) for run in runs),
        }
    capa_scores = {
        "avg_TR": mean(capa_tr_values),
        "avg_CR": mean(capa_cr_values),
        "avg_BPT": mean(capa_bpt_values),
    }
    best_baseline_tr = max((score["avg_TR"] for score in baseline_scores.values()), default=0.0)
    best_baseline_cr = max((score["avg_CR"] for score in baseline_scores.values()), default=0.0)
    tr_ratio = 1.0 if best_baseline_tr <= 0 else capa_scores["avg_TR"] / best_baseline_tr
    cr_gap = best_baseline_cr - capa_scores["avg_CR"]
    accepted = tr_ratio >= success_tr_ratio and cr_gap <= success_cr_gap
    if accepted:
        recommendation = "accept"
        diagnosis = "CAPA remains competitive on both revenue and completion rate under the managed threshold."
    elif cr_gap > success_cr_gap:
        recommendation = "retry-lower-threshold"
        diagnosis = "CAPA completion rate lags the strongest baseline, so the next round lowers omega."
    else:
        recommendation = "retry-detour-favoring"
        diagnosis = "CAPA completion stays close but TR lags, so the next round favors detour efficiency."
    return {
        "round": asdict(round_spec),
        "accepted": accepted,
        "recommendation": recommendation,
        "diagnosis": diagnosis,
        "capa_scores": capa_scores,
        "baseline_scores": baseline_scores,
        "best_baseline_TR": best_baseline_tr,
        "best_baseline_CR": best_baseline_cr,
        "tr_ratio_vs_best_baseline": tr_ratio,
        "cr_gap_vs_best_baseline": cr_gap,
    }


def run_chengdu_exp1_managed(
    script_path: Path,
    tmp_root: Path,
    final_output_dir: Path,
    algorithms: Sequence[str] = DEFAULT_CHENGDU_PAPER_ALGORITHMS,
    fixed_config_overrides: dict[str, Any] | None = None,
    preset_name: str = "formal",
    batch_size: int = 30,
    poll_seconds: int = 30,
    progress_mode: ProgressMode = "overwrite",
    round_specs: Sequence[Exp1RoundSpec] = DEFAULT_EXP1_ROUNDS,
    success_tr_ratio: float = 0.9,
    success_cr_gap: float = 0.02,
) -> dict[str, Any]:
    """Run managed Exp-1 rounds through the formal paper entrypoint.

    Args:
        script_path: Formal Exp-1 script path used for round subprocesses.
        tmp_root: Temporary managed root.
        final_output_dir: Final accepted-round destination.
        algorithms: Algorithms included in each round.
        fixed_config_overrides: Base fixed Chengdu config.
        preset_name: Exp-1 preset name.
        batch_size: Shared batch size.
        poll_seconds: Split poll interval.
        progress_mode: Terminal progress rendering mode.
        round_specs: Ordered CAPA parameter candidates.
        success_tr_ratio: Minimum CAPA TR ratio versus best baseline.
        success_cr_gap: Maximum allowed CAPA CR gap.

    Returns:
        Managed final manifest.
    """

    tmp_root.mkdir(parents=True, exist_ok=True)
    framework_rounds = [
        ManagedRoundSpec(
            name=round_spec.name,
            rationale=round_spec.rationale,
            runner_overrides_by_algorithm={"capa": dict(round_spec.capa_runner_kwargs)},
        )
        for round_spec in round_specs
    ]

    def round_output_dir_builder(round_index: int, round_spec: ManagedRoundSpec) -> Path:
        return tmp_root / f"round_{round_index:02d}_{round_spec.name}"

    def round_executor(round_spec: ManagedRoundSpec, round_output_dir: Path) -> dict[str, Any]:
        round_tmp_root = round_output_dir / "tmp"
        return run_chengdu_paper_split_experiment(
            axis="num_parcels",
            script_path=script_path,
            tmp_root=round_tmp_root,
            output_dir=round_output_dir,
            algorithms=algorithms,
            fixed_config_overrides={
                **(fixed_config_overrides or {}),
                "batch_size": batch_size,
            },
            preset_name=preset_name,
            poll_seconds=poll_seconds,
            progress_mode=progress_mode,
            runner_overrides_by_algorithm=dict(round_spec.runner_overrides_by_algorithm),
        )

    def round_analyzer(summary: dict[str, Any], round_spec: ManagedRoundSpec) -> dict[str, Any]:
        translated = Exp1RoundSpec(
            name=round_spec.name,
            rationale=round_spec.rationale,
            capa_runner_kwargs=dict(round_spec.runner_overrides_by_algorithm.get("capa", {})),
        )
        analysis = analyze_exp1_summary(
            summary=summary,
            algorithms=algorithms,
            round_spec=translated,
            success_tr_ratio=success_tr_ratio,
            success_cr_gap=success_cr_gap,
        )
        round_output_dir = next(tmp_root.glob(f"round_*_{round_spec.name}"))
        with (round_output_dir / "analysis.json").open("w", encoding="utf-8") as handle:
            json.dump(analysis, handle, indent=2)
        return analysis

    def round_promoter(round_output_dir: Path) -> None:
        if final_output_dir.exists():
            shutil.rmtree(final_output_dir)
        shutil.copytree(round_output_dir, final_output_dir)

    manifest = run_managed_rounds(
        round_specs=framework_rounds,
        round_output_dir_builder=round_output_dir_builder,
        round_executor=round_executor,
        round_analyzer=round_analyzer,
        round_promoter=round_promoter,
    )
    with (tmp_root / "final_manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
    return manifest


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
        task_window_start_seconds=fixed_config["task_window_start_seconds"],
        task_window_end_seconds=fixed_config["task_window_end_seconds"],
        task_sampling_seed=int(fixed_config["task_sampling_seed"]),
        partner_history_task_count_start=int(fixed_config["partner_history_task_count_start"]),
        partner_history_task_count_step=int(fixed_config["partner_history_task_count_step"]),
        courier_alpha=float(fixed_config["courier_alpha"]),
        courier_beta=float(fixed_config["courier_beta"]) if fixed_config["courier_beta"] is not None else None,
        courier_service_score=float(fixed_config["courier_service_score"]),
        platform_quality_start=float(fixed_config["platform_quality_start"]),
        platform_quality_step=float(fixed_config["platform_quality_step"]),
    )
    from .seeding import build_environment_seed, clone_environment_from_seed

    seed = build_environment_seed(environment)
    output_dir.mkdir(parents=True, exist_ok=True)
    summaries: dict[str, Any] = {}
    for algorithm in algorithms:
        runner_kwargs = {"batch_size": int(fixed_config["batch_size"])} if algorithm in {"capa", "greedy", "mra"} else {}
        if algorithm == "impgta":
            runner_kwargs = {
                "prediction_window_seconds": int(fixed_config["prediction_window_seconds"]),
                "prediction_success_rate": float(fixed_config["prediction_success_rate"]),
                "prediction_sampling_seed": int(fixed_config["prediction_sampling_seed"]),
            }
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
    parser.add_argument("--execution-mode", choices=PAPER_EXECUTION_MODES, default="direct")
    parser.add_argument("--point-value", type=float, default=None, help="Single sweep-point value used by point mode.")
    parser.add_argument("--tmp-root", default=None, help="Temporary split root used by split or managed runs.")
    parser.add_argument("--seed-path", default=None, help="Optional canonical seed path reused by point/split runs.")
    parser.add_argument("--poll-seconds", type=int, default=30, help="Split progress polling interval in seconds.")
    parser.add_argument("--progress-mode", choices=("overwrite", "append", "auto"), default="overwrite")
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
    parser.add_argument("--prediction-window-seconds", type=int, default=DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["prediction_window_seconds"])
    parser.add_argument("--task-window-start-seconds", type=float, default=DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["task_window_start_seconds"])
    parser.add_argument("--task-window-end-seconds", type=float, default=DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["task_window_end_seconds"])
    parser.add_argument("--task-sampling-seed", type=int, default=DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["task_sampling_seed"])
    parser.add_argument("--partner-history-task-count-start", type=int, default=DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["partner_history_task_count_start"])
    parser.add_argument("--partner-history-task-count-step", type=int, default=DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["partner_history_task_count_step"])
    parser.add_argument("--prediction-success-rate", type=float, default=DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["prediction_success_rate"])
    parser.add_argument("--prediction-sampling-seed", type=int, default=DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["prediction_sampling_seed"])
    parser.add_argument("--courier-alpha", type=float, default=DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["courier_alpha"])
    parser.add_argument("--courier-beta", type=float, default=DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["courier_beta"])
    parser.add_argument("--courier-service-score", type=float, default=DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["courier_service_score"])
    parser.add_argument("--platform-quality-start", type=float, default=DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["platform_quality_start"])
    parser.add_argument("--platform-quality-step", type=float, default=DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["platform_quality_step"])
    parser.add_argument("--rl-future-feature-window-seconds", type=int, default=DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["rl_future_feature_window_seconds"])
    parser.add_argument("--success-tr-ratio", type=float, default=0.9)
    parser.add_argument("--success-cr-gap", type=float, default=0.02)
    parser.add_argument("--utility-balance-gamma", type=float, default=None)
    parser.add_argument("--threshold-omega", type=float, default=None)
    parser.add_argument("--local-payment-ratio-zeta", type=float, default=None)
    parser.add_argument("--local-sharing-rate-mu1", type=float, default=None)
    parser.add_argument("--cross-platform-sharing-rate-mu2", type=float, default=None)
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
        "prediction_window_seconds": args.prediction_window_seconds,
        "prediction_success_rate": args.prediction_success_rate,
        "prediction_sampling_seed": args.prediction_sampling_seed,
        "task_window_start_seconds": args.task_window_start_seconds,
        "task_window_end_seconds": args.task_window_end_seconds,
        "task_sampling_seed": args.task_sampling_seed,
        "partner_history_task_count_start": getattr(
            args,
            "partner_history_task_count_start",
            DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["partner_history_task_count_start"],
        ),
        "partner_history_task_count_step": getattr(
            args,
            "partner_history_task_count_step",
            DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["partner_history_task_count_step"],
        ),
        "courier_alpha": getattr(args, "courier_alpha", DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["courier_alpha"]),
        "courier_beta": getattr(args, "courier_beta", DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["courier_beta"]),
        "courier_service_score": getattr(args, "courier_service_score", DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["courier_service_score"]),
        "platform_quality_start": getattr(args, "platform_quality_start", DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["platform_quality_start"]),
        "platform_quality_step": getattr(args, "platform_quality_step", DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["platform_quality_step"]),
        "rl_future_feature_window_seconds": getattr(args, "rl_future_feature_window_seconds", DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["rl_future_feature_window_seconds"]),
    }


def build_capa_runner_overrides_from_args(args: argparse.Namespace) -> dict[str, dict[str, Any]]:
    """Translate optional CLI CAPA parameter overrides into runner override payloads."""

    overrides = {
        key: value
        for key, value in {
            "utility_balance_gamma": args.utility_balance_gamma,
            "threshold_omega": args.threshold_omega,
            "local_payment_ratio_zeta": args.local_payment_ratio_zeta,
            "local_sharing_rate_mu1": args.local_sharing_rate_mu1,
            "cross_platform_sharing_rate_mu2": args.cross_platform_sharing_rate_mu2,
        }.items()
        if value is not None
    }
    return {} if not overrides else {"capa": overrides}


def build_paper_runner_overrides_from_fixed_config(
    fixed_config: dict[str, Any],
    explicit_overrides: dict[str, dict[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    """Build per-algorithm runner overrides implied by paper fixed config.

    Args:
        fixed_config: Shared paper fixed configuration.
        explicit_overrides: Optional caller-provided overrides to merge on top.

    Returns:
        Per-algorithm runner kwargs that should be honored by point/split runners.
    """

    merged: dict[str, dict[str, Any]] = {
        "impgta": {
            "prediction_window_seconds": int(fixed_config["prediction_window_seconds"]),
            "prediction_success_rate": float(fixed_config["prediction_success_rate"]),
            "prediction_sampling_seed": int(fixed_config["prediction_sampling_seed"]),
        },
        "rl-capa": {
            "future_feature_window_seconds": int(
                fixed_config.get(
                    "rl_future_feature_window_seconds",
                    DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["rl_future_feature_window_seconds"],
                )
            ),
        }
    }
    for algorithm, overrides in (explicit_overrides or {}).items():
        merged.setdefault(algorithm, {})
        merged[algorithm].update(dict(overrides))
    return merged


def _build_paper_runner(
    algorithm_name: str,
    runner_overrides_by_algorithm: dict[str, dict[str, Any]] | None = None,
    **kwargs: object,
) -> Any:
    """Build one algorithm runner while honoring optional per-algorithm overrides."""

    merged_kwargs = dict(kwargs)
    if runner_overrides_by_algorithm and algorithm_name in runner_overrides_by_algorithm:
        merged_kwargs.update(dict(runner_overrides_by_algorithm[algorithm_name]))
    return build_algorithm_runner(algorithm_name, **merged_kwargs)


def _experiment_label_for_axis(axis: str) -> str:
    """Return the human-readable experiment title for one paper axis."""

    labels = {
        "num_parcels": "Exp-1",
        "local_couriers": "Exp-2",
        "service_radius": "Exp-3",
        "platforms": "Exp-4",
        "batch_size": "Exp-5",
        "courier_capacity": "Exp-6",
        "courier_alpha": "Exp-Alpha",
    }
    return labels.get(axis, "Experiment")


def _build_capa_override_cli_args(capa_runner_kwargs: dict[str, Any]) -> list[str]:
    """Translate CAPA override kwargs into CLI arguments for formal point scripts."""

    mapping = {
        "utility_balance_gamma": "--utility-balance-gamma",
        "threshold_omega": "--threshold-omega",
        "local_payment_ratio_zeta": "--local-payment-ratio-zeta",
        "local_sharing_rate_mu1": "--local-sharing-rate-mu1",
        "cross_platform_sharing_rate_mu2": "--cross-platform-sharing-rate-mu2",
    }
    args: list[str] = []
    for key, flag in mapping.items():
        if key in capa_runner_kwargs:
            args.extend([flag, str(capa_runner_kwargs[key])])
    return args


def _canonical_environment_kwargs_for_axis(
    axis: str,
    axis_values: Sequence[int | float],
    fixed_config: dict[str, Any],
) -> dict[str, Any]:
    """Build canonical Chengdu environment kwargs for one paper sweep axis.

    Args:
        axis: Sweep axis name.
        axis_values: Ordered preset values for the axis.
        fixed_config: Shared fixed configuration for the experiment.

    Returns:
        Environment build kwargs used to create a canonical seed.
    """

    kwargs = {
        "data_dir": Path(fixed_config["data_dir"]),
        "num_parcels": int(fixed_config["num_parcels"]),
        "local_courier_count": int(fixed_config["local_couriers"]),
        "cooperating_platform_count": int(fixed_config["platforms"]),
        "couriers_per_platform": int(fixed_config["couriers_per_platform"]),
        "service_radius_km": fixed_config["service_radius_km"],
        "courier_capacity": fixed_config["courier_capacity"],
        "task_window_start_seconds": fixed_config["task_window_start_seconds"],
        "task_window_end_seconds": fixed_config["task_window_end_seconds"],
        "task_sampling_seed": int(fixed_config["task_sampling_seed"]),
        "partner_history_task_count_start": int(fixed_config["partner_history_task_count_start"]),
        "partner_history_task_count_step": int(fixed_config["partner_history_task_count_step"]),
        "courier_alpha": float(fixed_config["courier_alpha"]),
        "courier_beta": float(fixed_config["courier_beta"]) if fixed_config["courier_beta"] is not None else None,
        "courier_service_score": float(fixed_config["courier_service_score"]),
        "platform_quality_start": float(fixed_config["platform_quality_start"]),
        "platform_quality_step": float(fixed_config["platform_quality_step"]),
    }
    if axis == "num_parcels":
        kwargs["num_parcels"] = max(int(value) for value in axis_values)
    elif axis == "local_couriers":
        kwargs["local_courier_count"] = max(int(value) for value in axis_values)
    elif axis == "platforms":
        kwargs["cooperating_platform_count"] = max(int(value) for value in axis_values)
    elif axis == "courier_capacity":
        kwargs["courier_capacity"] = min(float(value) for value in axis_values)
    elif axis == "service_radius":
        pass
    elif axis == "batch_size":
        pass
    elif axis == "courier_alpha":
        kwargs["courier_alpha"] = float(fixed_config["courier_alpha"])
        kwargs["courier_beta"] = float(fixed_config["courier_beta"]) if fixed_config["courier_beta"] is not None else None
    else:
        raise ValueError(f"Unsupported canonical seed axis: {axis}")
    return kwargs


def _write_point_bootstrap_progress(
    output_dir: Path,
    axis: str,
    axis_value: int | float,
    total_algorithms: int,
    detail: str,
) -> None:
    """Persist an initial point-progress snapshot before environment construction starts.

    Args:
        output_dir: Point-level output directory.
        axis: Sweep axis name.
        axis_value: Concrete point value.
        total_algorithms: Number of algorithms in the point.
        detail: Human-readable startup detail text.
    """

    write_point_progress(
        output_dir / "progress.json",
        build_point_progress_snapshot(
            axis_name=axis,
            axis_value=axis_value,
            algorithm="-",
            algorithm_index=0,
            total_algorithms=total_algorithms,
            completed_algorithms=[],
            state="running",
            last_event={"phase": "initializing", "detail": detail},
        ),
    )
