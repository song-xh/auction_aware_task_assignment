"""Exp-7 robustness mode: dual-environment delay comparison for CAPA vs RL-CAPA.

This module wraps a single experiment configuration into a baseline-vs-delay
comparison: one canonical Chengdu environment is built with a fixed
``task_sampling_seed`` and then cloned twice. Clone A keeps raw arrival
times; Clone B applies a window-bounded processing delay (only parcels
whose true arrival lies inside ``delay_window`` are pushed by
``delay_seconds``). Both clones run the same algorithm, and the resulting
per-parcel decision traces are diffed so robustness can be measured by how
many affected parcels keep their decision under the perturbation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from algorithms.registry import build_algorithm_runner
from env.chengdu import ChengduEnvironment
from experiments.deadline_disturbance import (
    apply_processing_delay,
    parse_delay_window,
)
from experiments.seeding import (
    ChengduEnvironmentSeed,
    build_environment_seed,
    clone_environment_from_seed,
)


@dataclass(frozen=True)
class DelaySpec:
    """One delay-window perturbation specifier."""

    delay_seconds: float
    window: tuple[float, float]

    @classmethod
    def from_cli(cls, delay_seconds: float, delay_window: str) -> "DelaySpec":
        """Build a :class:`DelaySpec` from CLI strings.

        Args:
            delay_seconds: Delay duration in seconds (must be non-negative).
            delay_window: ``"start,end"`` window of true arrival times.

        Returns:
            DelaySpec with parsed window.
        """

        if delay_seconds < 0:
            raise ValueError("delay_seconds must be non-negative.")
        return cls(delay_seconds=float(delay_seconds), window=parse_delay_window(delay_window))


@dataclass
class _AlgoRobustness:
    """One algorithm's baseline vs delayed metrics + decision diff."""

    algorithm: str
    baseline_metrics: dict[str, Any] = field(default_factory=dict)
    delayed_metrics: dict[str, Any] = field(default_factory=dict)
    affected_transitions: list[dict[str, Any]] = field(default_factory=list)
    transition_counts: dict[str, int] = field(default_factory=dict)


def _index_trace(trace: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    """Index a decision trace by ``parcel_id`` for O(1) lookup."""

    return {str(entry.get("parcel_id", "")): entry for entry in trace}


def _diff_decision_states(
    baseline_trace: Sequence[Mapping[str, Any]],
    delayed_trace: Sequence[Mapping[str, Any]],
    affected_parcel_ids: Iterable[str],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Compare baseline vs delayed decisions for affected parcels.

    Returns the per-parcel transition list and a counts summary keyed by
    ``"<baseline_outcome>__<delayed_outcome>"``. Outcome categories are:
    ``delivered_local``, ``delivered_cross``, ``timed_out``, ``unmatched``,
    ``missing`` (entry absent from a trace).
    """

    baseline_index = _index_trace(baseline_trace)
    delayed_index = _index_trace(delayed_trace)
    transitions: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    for parcel_id in affected_parcel_ids:
        baseline_entry = baseline_index.get(parcel_id)
        delayed_entry = delayed_index.get(parcel_id)
        baseline_outcome = _categorize_outcome(baseline_entry)
        delayed_outcome = _categorize_outcome(delayed_entry)
        key = f"{baseline_outcome}__{delayed_outcome}"
        counts[key] = counts.get(key, 0) + 1
        transitions.append(
            {
                "parcel_id": parcel_id,
                "baseline": _trimmed_entry(baseline_entry),
                "delayed": _trimmed_entry(delayed_entry),
                "baseline_outcome": baseline_outcome,
                "delayed_outcome": delayed_outcome,
            }
        )
    return transitions, counts


def _categorize_outcome(entry: Mapping[str, Any] | None) -> str:
    """Map one decision-trace entry into a coarse outcome label."""

    if entry is None:
        return "missing"
    mode = str(entry.get("mode", ""))
    if mode == "unmatched":
        return "unmatched"
    if not bool(entry.get("delivered", False)):
        return "timed_out"
    if mode == "cross":
        return "delivered_cross"
    return "delivered_local"


def _trimmed_entry(entry: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """Return a compact JSON-friendly copy of a decision-trace entry."""

    if entry is None:
        return None
    return {
        "mode": entry.get("mode"),
        "courier_id": entry.get("courier_id"),
        "delivered": entry.get("delivered"),
        "on_time": entry.get("on_time"),
        "local_platform_revenue": entry.get("local_platform_revenue"),
    }


def _affected_parcel_ids(environment: ChengduEnvironment) -> list[str]:
    """Return parcel ids tagged with ``is_delayed=True`` in the perturbed env."""

    return [
        str(getattr(task, "num"))
        for task in environment.tasks
        if bool(getattr(task, "is_delayed", False))
    ]


def _run_one_algorithm(
    algorithm: str,
    environment: ChengduEnvironment,
    runner_kwargs: Mapping[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    """Build the registered runner, execute against ``environment``, return summary."""

    output_dir.mkdir(parents=True, exist_ok=True)
    runner = build_algorithm_runner(algorithm, **dict(runner_kwargs))
    return runner.run(environment=environment, output_dir=output_dir)


def run_exp7_robustness(
    canonical_environment: ChengduEnvironment,
    delay_spec: DelaySpec,
    algorithms: Sequence[str],
    output_dir: Path,
    runner_kwargs_by_algorithm: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run baseline + delayed comparison for every algorithm and persist results.

    Args:
        canonical_environment: Pre-built Chengdu environment whose tasks/seed
            are reused for both clones.
        delay_spec: Delay duration + window perturbation specifier.
        algorithms: Algorithm identifiers from the registry. Typically
            ``("capa", "rl-capa-infer")`` for robustness comparison.
        output_dir: Root directory receiving per-algorithm summaries and
            the aggregated ``robustness_comparison.json``.
        runner_kwargs_by_algorithm: Optional algorithm-specific kwargs
            (e.g. ``{"rl-capa-infer": {"checkpoint_dir": "..."}}``).

    Returns:
        JSON-serializable comparison payload.
    """

    output_dir.mkdir(parents=True, exist_ok=True)
    seed = build_environment_seed(canonical_environment)
    baseline_env = clone_environment_from_seed(seed)
    apply_processing_delay(baseline_env.tasks, delay_seconds=0.0, window=delay_spec.window)
    delayed_env = clone_environment_from_seed(seed)
    apply_processing_delay(
        delayed_env.tasks,
        delay_seconds=delay_spec.delay_seconds,
        window=delay_spec.window,
    )
    affected_ids = _affected_parcel_ids(delayed_env)
    runner_kwargs = dict(runner_kwargs_by_algorithm or {})
    per_algo: dict[str, dict[str, Any]] = {}
    for algorithm in algorithms:
        algo_dir = output_dir / algorithm
        baseline_summary = _run_one_algorithm(
            algorithm=algorithm,
            environment=clone_environment_from_seed(seed),
            runner_kwargs=runner_kwargs.get(algorithm, {}),
            output_dir=algo_dir / "baseline",
        )
        delayed_summary = _run_one_algorithm(
            algorithm=algorithm,
            environment=delayed_env,
            runner_kwargs=runner_kwargs.get(algorithm, {}),
            output_dir=algo_dir / "delayed",
        )
        transitions, counts = _diff_decision_states(
            baseline_trace=baseline_summary.get("decision_trace", []),
            delayed_trace=delayed_summary.get("decision_trace", []),
            affected_parcel_ids=affected_ids,
        )
        per_algo[algorithm] = {
            "baseline_metrics": dict(baseline_summary.get("metrics", {})),
            "delayed_metrics": dict(delayed_summary.get("metrics", {})),
            "affected_transitions": transitions,
            "transition_counts": counts,
            "summary_paths": {
                "baseline": str(algo_dir / "baseline" / "summary.json"),
                "delayed": str(algo_dir / "delayed" / "summary.json"),
            },
        }
        # Rebuild the delayed env clone for the next algorithm so a stateful
        # runner cannot leak side-effects from one algorithm to the next.
        delayed_env = clone_environment_from_seed(seed)
        apply_processing_delay(
            delayed_env.tasks,
            delay_seconds=delay_spec.delay_seconds,
            window=delay_spec.window,
        )

    comparison = {
        "delay_spec": {
            "delay_seconds": delay_spec.delay_seconds,
            "window": list(delay_spec.window),
        },
        "affected_parcel_count": len(affected_ids),
        "affected_parcel_ids": affected_ids,
        "per_algorithm": per_algo,
    }
    with (output_dir / "robustness_comparison.json").open("w", encoding="utf-8") as handle:
        json.dump(comparison, handle, indent=2)
    return comparison
