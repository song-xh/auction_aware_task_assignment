"""Unified CAPA strategy wrapper for the root algorithm registry."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from capa.experiments import build_default_chengdu_config, save_experiment_plots
from env.chengdu import run_time_stepped_chengdu_batches

from .base import AlgorithmRunner


class CAPAAlgorithmRunner(AlgorithmRunner):
    """Run the paper-faithful CAPA logic against a prepared Chengdu environment."""

    def __init__(self, batch_size: int = 300) -> None:
        """Store the CAPA batch window used by the environment-backed runner."""
        self._batch_size = batch_size

    def run(self, environment: Any, output_dir: Path | None = None) -> dict[str, Any]:
        """Execute CAPA on the provided Chengdu environment and return a normalized summary."""
        config = build_default_chengdu_config(batch_size=self._batch_size)
        result = run_time_stepped_chengdu_batches(
            tasks=environment.tasks,
            local_couriers=environment.local_couriers,
            partner_couriers_by_platform=environment.partner_couriers_by_platform,
            station_set=environment.station_set,
            travel_model=environment.travel_model,
            config=config,
            batch_seconds=self._batch_size,
            step_seconds=60,
            platform_base_prices=environment.platform_base_prices,
            platform_sharing_rates=environment.platform_sharing_rates,
            platform_qualities=environment.platform_qualities,
            movement_callback=environment.movement_callback,
        )
        summary = {
            "algorithm": "capa",
            "batch_size": self._batch_size,
            "metrics": {
                "TR": result.metrics.total_revenue,
                "CR": result.metrics.completion_rate,
                "BPT": result.metrics.batch_processing_time,
                "delivered_parcels": result.metrics.delivered_parcel_count,
                "accepted_assignments": result.metrics.accepted_parcel_count,
            },
        }
        if output_dir is not None:
            output_dir.mkdir(parents=True, exist_ok=True)
            save_experiment_plots(result.batch_reports, result.metrics, output_dir)
            with (output_dir / "summary.json").open("w", encoding="utf-8") as handle:
                json.dump(summary, handle, indent=2)
        return summary


def build_capa_runner(batch_size: int = 300) -> CAPAAlgorithmRunner:
    """Build the unified CAPA runner with the provided batch window."""
    return CAPAAlgorithmRunner(batch_size=batch_size)
