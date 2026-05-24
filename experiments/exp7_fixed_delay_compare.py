"""Fixed-data Exp-7 delay comparison for CAPA, ImpGTA, and RamCOM."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from algorithms.registry import build_algorithm_runner
from env.chengdu import get_model_release_time, get_true_deadline, get_true_release_time
from experiments.deadline_disturbance import apply_processing_delay
from experiments.exp7_robustness import _affected_parcel_ids, _diff_decision_states
from experiments.seeding import (
    build_environment_seed,
    clone_environment_from_seed,
    load_environment_seed,
    save_environment_seed,
)


DEFAULT_FIXED_DELAY_VALUES = (5, 10, 20, 30, 60)
_SUMMARY_METRIC_KEYS = (
    "TR",
    "CR",
    "BPT",
    "delivered_parcels",
    "accepted_assignments",
    "timed_out_parcels",
)
_OUTCOME_KEYS = (
    "delivered_local",
    "delivered_cross",
    "timed_out",
    "unmatched",
    "missing",
)
_DATA_MODES = {"auto", "reuse", "regenerate"}


def prepare_exp7_delay_datasets(
    canonical_environment: Any,
    data_cache_dir: Path,
    delay_values: Sequence[int | float],
    delay_window: tuple[float, float],
    data_mode: str = "auto",
) -> dict[str, Any]:
    """Prepare fixed Exp-7 CSV artifacts by reusing or regenerating the cache.

    Args:
        canonical_environment: Canonical Chengdu environment used for regeneration.
        data_cache_dir: Directory holding the manifest and exported CSV files.
        delay_values: Delay durations in seconds to materialize.
        delay_window: Inclusive true-arrival window receiving the delay.
        data_mode: One of `auto`, `reuse`, or `regenerate`.

    Returns:
        Export manifest describing the fixed dataset artifacts.

    Raises:
        FileNotFoundError: When `data_mode="reuse"` is requested but no
            existing manifest is present.
        ValueError: When `data_mode` is unsupported.
    """

    normalized_mode = str(data_mode).strip().lower()
    if normalized_mode not in _DATA_MODES:
        raise ValueError(f"Unsupported data_mode: {data_mode!r}. Expected one of {sorted(_DATA_MODES)}.")
    manifest_path = data_cache_dir / "manifest.json"
    if normalized_mode in {"auto", "reuse"} and manifest_path.exists():
        return _load_dataset_manifest(manifest_path)
    if normalized_mode == "reuse":
        raise FileNotFoundError(f"Expected existing dataset manifest at {manifest_path}.")
    return export_exp7_delay_datasets(
        canonical_environment=canonical_environment,
        data_cache_dir=data_cache_dir,
        delay_values=delay_values,
        delay_window=delay_window,
    )


def export_exp7_delay_datasets(
    canonical_environment: Any,
    data_cache_dir: Path,
    delay_values: Sequence[int | float],
    delay_window: tuple[float, float],
) -> dict[str, Any]:
    """Export canonical and delayed Exp-7 task CSVs under one fixed cache directory.

    Args:
        canonical_environment: Canonical Chengdu environment or compatible stub.
        data_cache_dir: Directory receiving CSV exports and, when possible, the
            replayable environment seed.
        delay_values: Delay durations in seconds to materialize.
        delay_window: Inclusive true-arrival window receiving the delay.

    Returns:
        Manifest describing the generated artifact paths.
    """

    data_cache_dir.mkdir(parents=True, exist_ok=True)
    seed = _try_build_seed(canonical_environment)
    seed_path: Path | None = None
    if seed is not None:
        seed_path = data_cache_dir / "canonical-environment-seed.pkl"
        save_environment_seed(seed, seed_path)

    canonical_tasks = _canonical_tasks(canonical_environment, seed)
    canonical_pickup_path = data_cache_dir / "pick-up-parcels.csv"
    _write_task_csv(canonical_pickup_path, canonical_tasks)

    partner_paths: dict[str, str] = {}
    for platform_id, platform_tasks in sorted((getattr(canonical_environment, "partner_tasks_by_platform", {}) or {}).items()):
        partner_path = data_cache_dir / f"partner-tasks-{platform_id}.csv"
        _write_task_csv(partner_path, _sort_tasks(platform_tasks), platform_id=platform_id)
        partner_paths[str(platform_id)] = str(partner_path)

    delayed_paths: dict[str, str] = {}
    for delay_value in delay_values:
        delayed_tasks = _clone_tasks(canonical_tasks)
        apply_processing_delay(delayed_tasks, delay_seconds=float(delay_value), window=delay_window)
        delay_label = _delay_label(delay_value)
        delayed_path = data_cache_dir / f"pick-up-parcels-delay-{delay_label}.csv"
        _write_task_csv(delayed_path, delayed_tasks)
        delayed_paths[str(delay_value)] = str(delayed_path)

    manifest = {
        "data_cache_dir": str(data_cache_dir),
        "seed_path": None if seed_path is None else str(seed_path),
        "canonical_pickup_path": str(canonical_pickup_path),
        "partner_task_paths": partner_paths,
        "delayed_pickup_paths": delayed_paths,
        "delay_window": [float(delay_window[0]), float(delay_window[1])],
    }
    with (data_cache_dir / "manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
    return manifest


def summarize_delay_run(
    baseline_summary: Mapping[str, Any],
    delayed_summary: Mapping[str, Any],
    affected_parcel_ids: Iterable[str],
) -> dict[str, Any]:
    """Build one affected-parcel comparison payload for a delayed run."""

    affected_ids = [str(parcel_id) for parcel_id in affected_parcel_ids]
    transitions, counts = _diff_decision_states(
        baseline_trace=list(baseline_summary.get("decision_trace", [])),
        delayed_trace=list(delayed_summary.get("decision_trace", [])),
        affected_parcel_ids=affected_ids,
    )
    return {
        "affected_parcel_count": len(affected_ids),
        "affected_parcel_ids": affected_ids,
        "metric_deltas": _metric_deltas(
            baseline_metrics=dict(baseline_summary.get("metrics", {})),
            delayed_metrics=dict(delayed_summary.get("metrics", {})),
        ),
        "affected_transitions": transitions,
        "transition_counts": counts,
        "affected_outcome_totals": _affected_outcome_totals(transitions),
    }


def run_exp7_fixed_delay_compare(
    canonical_environment: Any,
    delay_values: Sequence[int | float],
    delay_window: tuple[float, float],
    algorithms: Sequence[str],
    output_dir: Path,
    data_cache_dir: Path,
    data_mode: str = "auto",
    runner_kwargs_by_algorithm: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run baseline plus multiple delay comparisons for the requested algorithms."""

    output_dir.mkdir(parents=True, exist_ok=True)
    data_manifest = prepare_exp7_delay_datasets(
        canonical_environment=canonical_environment,
        data_cache_dir=data_cache_dir,
        delay_values=delay_values,
        delay_window=delay_window,
        data_mode=data_mode,
    )
    canonical_environment = resolve_canonical_environment(
        canonical_environment=canonical_environment,
        data_manifest=data_manifest,
        data_mode=data_mode,
    )
    seed = build_environment_seed(canonical_environment)
    runner_kwargs_by_algorithm = dict(runner_kwargs_by_algorithm or {})
    delayed_envs: dict[str, Any] = {}
    affected_ids_by_delay: dict[str, list[str]] = {}
    for delay_value in delay_values:
        delay_key = str(delay_value)
        delayed_env = clone_environment_from_seed(seed)
        apply_processing_delay(delayed_env.tasks, delay_seconds=float(delay_value), window=delay_window)
        delayed_envs[delay_key] = delayed_env
        affected_ids_by_delay[delay_key] = _affected_parcel_ids(delayed_env)

    per_algorithm: dict[str, Any] = {}
    for algorithm in algorithms:
        algorithm_dir = output_dir / algorithm
        baseline_summary = _run_one_algorithm(
            algorithm=algorithm,
            environment=clone_environment_from_seed(seed),
            runner_kwargs=runner_kwargs_by_algorithm.get(algorithm, {}),
            output_dir=algorithm_dir / "baseline",
        )
        per_delay: dict[str, Any] = {}
        for delay_value in delay_values:
            delay_key = str(delay_value)
            delayed_summary = _run_one_algorithm(
                algorithm=algorithm,
                environment=clone_environment_from_seed(build_environment_seed(delayed_envs[delay_key])),
                runner_kwargs=runner_kwargs_by_algorithm.get(algorithm, {}),
                output_dir=algorithm_dir / f"delay-{_delay_label(delay_value)}",
            )
            comparison = summarize_delay_run(
                baseline_summary=baseline_summary,
                delayed_summary=delayed_summary,
                affected_parcel_ids=affected_ids_by_delay[delay_key],
            )
            comparison.update(
                {
                    "delay_seconds": float(delay_value),
                    "baseline_metrics": dict(baseline_summary.get("metrics", {})),
                    "delayed_metrics": dict(delayed_summary.get("metrics", {})),
                    "summary_paths": {
                        "baseline": str(algorithm_dir / "baseline" / "summary.json"),
                        "delayed": str(algorithm_dir / f"delay-{_delay_label(delay_value)}" / "summary.json"),
                    },
                }
            )
            per_delay[delay_key] = comparison
        per_algorithm[algorithm] = {
            "baseline_metrics": dict(baseline_summary.get("metrics", {})),
            "baseline_summary_path": str(algorithm_dir / "baseline" / "summary.json"),
            "delays": per_delay,
        }

    summary = {
        "algorithms": list(algorithms),
        "data_mode": str(data_mode),
        "delay_window": [float(delay_window[0]), float(delay_window[1])],
        "delay_values": [float(value) for value in delay_values],
        "data_manifest": data_manifest,
        "affected_parcel_ids_by_delay": affected_ids_by_delay,
        "per_algorithm": per_algorithm,
    }
    with (output_dir / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
    return summary


def _try_build_seed(canonical_environment: Any) -> Any | None:
    """Return a replayable environment seed when the input is a real environment."""

    required_attributes = (
        "tasks",
        "local_couriers",
        "partner_couriers_by_platform",
        "station_set",
        "travel_model",
        "platform_base_prices",
        "platform_sharing_rates",
        "platform_qualities",
    )
    if not all(hasattr(canonical_environment, attribute) for attribute in required_attributes):
        return None
    return build_environment_seed(canonical_environment)


def _load_dataset_manifest(manifest_path: Path) -> dict[str, Any]:
    """Load one previously exported fixed-data manifest from disk."""

    with manifest_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def resolve_canonical_environment(
    canonical_environment: Any,
    data_manifest: Mapping[str, Any],
    data_mode: str,
) -> Any:
    """Resolve the canonical environment used for experiment execution.

    Reuse mode prefers the cached canonical seed so the runtime input exactly
    matches the persisted `Data/delay` artifacts. Regenerate mode uses the
    freshly built `canonical_environment`.
    """

    normalized_mode = str(data_mode).strip().lower()
    seed_path_value = data_manifest.get("seed_path")
    if normalized_mode == "regenerate" or not seed_path_value:
        return canonical_environment
    seed_path = Path(str(seed_path_value))
    if seed_path.exists():
        return clone_environment_from_seed(load_environment_seed(seed_path))
    if normalized_mode == "reuse":
        raise FileNotFoundError(f"Expected cached seed at {seed_path}.")
    return canonical_environment


def _canonical_tasks(canonical_environment: Any, seed: Any | None) -> list[Any]:
    """Return canonical local tasks in stable true-arrival order."""

    if seed is not None:
        return _sort_tasks(clone_environment_from_seed(seed).tasks)
    return _sort_tasks(getattr(canonical_environment, "tasks", []))


def _clone_tasks(tasks: Sequence[Any]) -> list[Any]:
    """Clone a sequence of task-like objects without assuming task classes."""

    from copy import deepcopy

    return deepcopy(list(tasks))


def _sort_tasks(tasks: Sequence[Any]) -> list[Any]:
    """Sort tasks by true release time, true deadline, and stable parcel id."""

    return sorted(
        list(tasks),
        key=lambda task: (
            get_true_release_time(task),
            get_true_deadline(task),
            str(getattr(task, "num")),
        ),
    )


def _write_task_csv(path: Path, tasks: Sequence[Any], platform_id: str | None = None) -> None:
    """Write one stable task CSV for human inspection and experiment auditing."""

    fieldnames = [
        "parcel_id",
        "platform_id",
        "true_release_time",
        "observed_release_time",
        "true_deadline",
        "observed_deadline",
        "is_delayed",
        "weight",
        "fare",
        "location_node",
        "lng",
        "lat",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for task in _sort_tasks(tasks):
            writer.writerow(
                {
                    "parcel_id": str(getattr(task, "num")),
                    "platform_id": "" if platform_id is None else str(platform_id),
                    "true_release_time": get_true_release_time(task),
                    "observed_release_time": get_model_release_time(task),
                    "true_deadline": get_true_deadline(task),
                    "observed_deadline": float(getattr(task, "observed_d_time", get_true_deadline(task))),
                    "is_delayed": bool(getattr(task, "is_delayed", False)),
                    "weight": float(getattr(task, "weight", 0.0)),
                    "fare": float(getattr(task, "fare", 0.0)),
                    "location_node": str(getattr(task, "l_node", "")),
                    "lng": float(getattr(task, "l_lng", 0.0)),
                    "lat": float(getattr(task, "l_lat", 0.0)),
                }
            )


def _delay_label(delay_value: int | float) -> str:
    """Return the stable filename label used for one delay duration."""

    delay_float = float(delay_value)
    if delay_float.is_integer():
        return f"{int(delay_float)}s"
    return f"{str(delay_float).replace('.', 'p')}s"


def _metric_deltas(
    baseline_metrics: Mapping[str, Any],
    delayed_metrics: Mapping[str, Any],
) -> dict[str, Any]:
    """Compute delayed-minus-baseline metric deltas for the summary payload."""

    deltas: dict[str, Any] = {}
    for key in _SUMMARY_METRIC_KEYS:
        delayed_value = delayed_metrics.get(key, 0)
        baseline_value = baseline_metrics.get(key, 0)
        delta = delayed_value - baseline_value
        if isinstance(delayed_value, float) or isinstance(baseline_value, float):
            delta = round(float(delta), 10)
        deltas[key] = delta
    return deltas


def _affected_outcome_totals(transitions: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, int]]:
    """Aggregate affected-parcel outcomes before and after one delay perturbation."""

    totals = {
        "baseline": {key: 0 for key in _OUTCOME_KEYS},
        "delayed": {key: 0 for key in _OUTCOME_KEYS},
    }
    for transition in transitions:
        baseline_key = str(transition.get("baseline_outcome", "missing"))
        delayed_key = str(transition.get("delayed_outcome", "missing"))
        totals["baseline"][baseline_key] = totals["baseline"].get(baseline_key, 0) + 1
        totals["delayed"][delayed_key] = totals["delayed"].get(delayed_key, 0) + 1
    return totals


def _run_one_algorithm(
    algorithm: str,
    environment: Any,
    runner_kwargs: Mapping[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    """Build one registered algorithm runner, execute it, and return the summary."""

    output_dir.mkdir(parents=True, exist_ok=True)
    runner = build_algorithm_runner(algorithm, **dict(runner_kwargs))
    return runner.run(environment=environment, output_dir=output_dir)
