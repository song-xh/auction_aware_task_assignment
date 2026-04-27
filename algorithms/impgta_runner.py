"""Unified ImpGTA strategy wrapper for the algorithm registry."""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Any, Callable, Mapping

from baselines.gta import run_impgta_baseline_environment
from capa.config import (
    DEFAULT_IMPGTA_PREDICTION_SAMPLING_SEED,
    DEFAULT_IMPGTA_PREDICTION_SUCCESS_RATE,
    DEFAULT_IMPGTA_WINDOW_SECONDS,
)

from .base import AlgorithmRunner
from .summary_utils import build_algorithm_summary


class ImpGTARunner(AlgorithmRunner):
    """Run ImpGTA through the unified environment interface."""

    def __init__(
        self,
        prediction_window_seconds: int = DEFAULT_IMPGTA_WINDOW_SECONDS,
        prediction_success_rate: float = DEFAULT_IMPGTA_PREDICTION_SUCCESS_RATE,
        prediction_sampling_seed: int = DEFAULT_IMPGTA_PREDICTION_SAMPLING_SEED,
        baseline_runner: Callable[..., dict[str, Any]] | None = None,
    ) -> None:
        """Store the ImpGTA future window and optional injected baseline runner."""
        self._prediction_window_seconds = prediction_window_seconds
        self._prediction_success_rate = prediction_success_rate
        self._prediction_sampling_seed = prediction_sampling_seed
        self._baseline_runner = baseline_runner or run_impgta_baseline_environment

    def run(
        self,
        environment: Any,
        output_dir: Path | None = None,
        progress_callback: Callable[[Mapping[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        """Execute ImpGTA against a prepared Chengdu environment and return a summary."""
        started_at = datetime.now().astimezone()
        metrics = self._baseline_runner(
            environment=environment,
            prediction_window_seconds=self._prediction_window_seconds,
            prediction_success_rate=self._prediction_success_rate,
            prediction_sampling_seed=self._prediction_sampling_seed,
            progress_callback=progress_callback,
        )
        finished_at = datetime.now().astimezone()
        summary = build_algorithm_summary(
            algorithm="impgta",
            environment=environment,
            metrics=metrics,
            local_assignment_count=int(metrics.get("local_assignment_count", metrics.get("accepted_assignments", 0))),
            cross_assignment_count=int(metrics.get("cross_assignment_count", 0)),
            unresolved_parcel_count=int(
                metrics.get(
                    "unresolved_parcel_count",
                    max(
                        0,
                        len(list(getattr(environment, "tasks", []))) - int(metrics.get("accepted_assignments", 0)),
                    ),
                )
            ),
            partner_cross_assignment_counts=metrics.get("partner_cross_assignment_counts", {}),
            partner_cross_revenues=metrics.get("partner_cross_revenues", {}),
            started_at=started_at,
            finished_at=finished_at,
            extra_fields={
                "prediction_window_seconds": self._prediction_window_seconds,
                "prediction_success_rate": self._prediction_success_rate,
                "prediction_sampling_seed": self._prediction_sampling_seed,
            },
        )
        if output_dir is not None:
            output_dir.mkdir(parents=True, exist_ok=True)
            with (output_dir / "summary.json").open("w", encoding="utf-8") as handle:
                json.dump(summary, handle, indent=2)
        return summary


def build_impgta_runner(
    prediction_window_seconds: int = DEFAULT_IMPGTA_WINDOW_SECONDS,
    prediction_success_rate: float = DEFAULT_IMPGTA_PREDICTION_SUCCESS_RATE,
    prediction_sampling_seed: int = DEFAULT_IMPGTA_PREDICTION_SAMPLING_SEED,
    baseline_runner: Callable[..., dict[str, Any]] | None = None,
) -> ImpGTARunner:
    """Build the unified ImpGTA runner."""
    return ImpGTARunner(
        prediction_window_seconds=prediction_window_seconds,
        prediction_success_rate=prediction_success_rate,
        prediction_sampling_seed=prediction_sampling_seed,
        baseline_runner=baseline_runner,
    )
