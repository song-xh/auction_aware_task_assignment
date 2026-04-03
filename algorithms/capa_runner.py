"""Unified CAPA strategy wrapper for the root algorithm registry."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from capa.experiments import save_experiment_plots
from capa.models import CAPAConfig
from env.chengdu import run_time_stepped_chengdu_batches

from .base import AlgorithmRunner


class CAPAAlgorithmRunner(AlgorithmRunner):
    """Run the paper-faithful CAPA logic against a prepared Chengdu environment."""

    def __init__(
        self,
        batch_size: int = 300,
        utility_balance_gamma: float = 0.5,
        threshold_omega: float = 1.0,
        local_payment_ratio_zeta: float = 0.2,
        local_sharing_rate_mu1: float = 0.5,
        cross_platform_sharing_rate_mu2: float = 0.4,
    ) -> None:
        """Store the CAPA configuration used by the environment-backed runner.

        Args:
            batch_size: Batch-size window in seconds.
            utility_balance_gamma: Eq.6 utility balance parameter.
            threshold_omega: Eq.7 threshold scale factor.
            local_payment_ratio_zeta: Local courier payment ratio.
            local_sharing_rate_mu1: Cross-platform first-layer sharing ratio.
            cross_platform_sharing_rate_mu2: Cross-platform second-layer sharing ratio.
        """

        self._batch_size = batch_size
        self._utility_balance_gamma = utility_balance_gamma
        self._threshold_omega = threshold_omega
        self._local_payment_ratio_zeta = local_payment_ratio_zeta
        self._local_sharing_rate_mu1 = local_sharing_rate_mu1
        self._cross_platform_sharing_rate_mu2 = cross_platform_sharing_rate_mu2

    def run(self, environment: Any, output_dir: Path | None = None) -> dict[str, Any]:
        """Execute CAPA on the provided Chengdu environment and return a normalized summary."""
        config = CAPAConfig(
            batch_size=self._batch_size,
            utility_balance_gamma=self._utility_balance_gamma,
            threshold_omega=self._threshold_omega,
            local_payment_ratio_zeta=self._local_payment_ratio_zeta,
            local_sharing_rate_mu1=self._local_sharing_rate_mu1,
            cross_platform_sharing_rate_mu2=self._cross_platform_sharing_rate_mu2,
        )
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
            service_radius_km=getattr(environment, "service_radius_km", None),
        )
        summary = {
            "algorithm": "capa",
            "batch_size": self._batch_size,
            "config": {
                "utility_balance_gamma": self._utility_balance_gamma,
                "threshold_omega": self._threshold_omega,
                "local_payment_ratio_zeta": self._local_payment_ratio_zeta,
                "local_sharing_rate_mu1": self._local_sharing_rate_mu1,
                "cross_platform_sharing_rate_mu2": self._cross_platform_sharing_rate_mu2,
            },
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


def build_capa_runner(
    batch_size: int = 300,
    utility_balance_gamma: float = 0.5,
    threshold_omega: float = 1.0,
    local_payment_ratio_zeta: float = 0.2,
    local_sharing_rate_mu1: float = 0.5,
    cross_platform_sharing_rate_mu2: float = 0.4,
) -> CAPAAlgorithmRunner:
    """Build the unified CAPA runner with the provided CAPA parameterization."""

    return CAPAAlgorithmRunner(
        batch_size=batch_size,
        utility_balance_gamma=utility_balance_gamma,
        threshold_omega=threshold_omega,
        local_payment_ratio_zeta=local_payment_ratio_zeta,
        local_sharing_rate_mu1=local_sharing_rate_mu1,
        cross_platform_sharing_rate_mu2=cross_platform_sharing_rate_mu2,
    )
