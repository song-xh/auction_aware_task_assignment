"""Unified ImpGTA strategy wrapper for the algorithm registry."""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Any, Callable, Mapping

from baselines.gta import DEFAULT_GTA_BATCH_SIZE_SECONDS, run_impgta_baseline_environment

from .base import AlgorithmRunner
from .summary_utils import build_algorithm_summary


class ImpGTARunner(AlgorithmRunner):
    """Run ImpGTA through the unified environment interface."""

    def __init__(
        self,
        batch_size: int = DEFAULT_GTA_BATCH_SIZE_SECONDS,
        baseline_runner: Callable[..., dict[str, Any]] | None = None,
        **_legacy_prediction_kwargs: Any,
    ) -> None:
        """Store the ImpGTA batch size and optional injected baseline runner.

        Legacy ``prediction_window_seconds`` / ``prediction_success_rate`` /
        ``prediction_sampling_seed`` kwargs are accepted-and-ignored so older
        configs still load. They no longer drive env behavior because impgta
        now shares the CAPA-aligned batch-end flow with basegta.
        """

        self._batch_size = batch_size
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
            batch_size=self._batch_size,
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
                "batch_size": self._batch_size,
            },
        )
        if output_dir is not None:
            output_dir.mkdir(parents=True, exist_ok=True)
            with (output_dir / "summary.json").open("w", encoding="utf-8") as handle:
                json.dump(summary, handle, indent=2)
        return summary


def build_impgta_runner(
    batch_size: int = DEFAULT_GTA_BATCH_SIZE_SECONDS,
    baseline_runner: Callable[..., dict[str, Any]] | None = None,
    **_legacy_prediction_kwargs: Any,
) -> ImpGTARunner:
    """Build the unified ImpGTA runner (impgta now shares basegta env flow)."""
    return ImpGTARunner(batch_size=batch_size, baseline_runner=baseline_runner)
