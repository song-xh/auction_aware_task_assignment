"""Unified RamCOM strategy wrapper for the algorithm registry."""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Any, Callable, Mapping

from baselines.ramcom import run_ramcom_baseline_environment
from capa.config import (
    DEFAULT_CAPA_BATCH_SIZE,
    DEFAULT_CROSS_PLATFORM_SHARING_RATE_MU2,
    DEFAULT_LOCAL_PAYMENT_RATIO_ZETA,
    DEFAULT_RAMCOM_MAX_OUTER_PAYMENT_RATIO,
    DEFAULT_RAMCOM_RANDOM_SEED,
)

from .base import AlgorithmRunner
from .summary_utils import build_algorithm_summary


class RamCOMAlgorithmRunner(AlgorithmRunner):
    """Run the Chengdu-adapted RamCOM baseline through the unified environment interface."""

    def __init__(
        self,
        batch_size: int = DEFAULT_CAPA_BATCH_SIZE,
        random_seed: int = DEFAULT_RAMCOM_RANDOM_SEED,
        local_payment_ratio_zeta: float = DEFAULT_LOCAL_PAYMENT_RATIO_ZETA,
        cross_platform_sharing_rate_mu2: float = DEFAULT_CROSS_PLATFORM_SHARING_RATE_MU2,
        max_outer_payment_ratio: float = DEFAULT_RAMCOM_MAX_OUTER_PAYMENT_RATIO,
        baseline_runner: Callable[..., dict[str, Any]] | None = None,
    ) -> None:
        """Store batch size, seed, revenue parameters, and optional injected runner."""
        self._batch_size = batch_size
        self._random_seed = random_seed
        self._local_payment_ratio_zeta = float(local_payment_ratio_zeta)
        self._cross_platform_sharing_rate_mu2 = float(cross_platform_sharing_rate_mu2)
        self._max_outer_payment_ratio = float(max_outer_payment_ratio)
        self._baseline_runner = baseline_runner or run_ramcom_baseline_environment

    def run(
        self,
        environment: Any,
        output_dir: Path | None = None,
        progress_callback: Callable[[Mapping[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        """Execute RamCOM against a prepared Chengdu environment and return a summary."""
        started_at = datetime.now().astimezone()
        metrics = self._baseline_runner(
            environment=environment,
            random_seed=self._random_seed,
            batch_size=self._batch_size,
            local_payment_ratio=self._local_payment_ratio_zeta,
            cross_platform_sharing_rate_mu2=self._cross_platform_sharing_rate_mu2,
            max_outer_payment_ratio=self._max_outer_payment_ratio,
            progress_callback=progress_callback,
        )
        finished_at = datetime.now().astimezone()
        decision_trace = list(metrics.get("decision_trace", []))
        summary_metrics = {
            key: value
            for key, value in metrics.items()
            if key != "decision_trace"
        }
        summary = build_algorithm_summary(
            algorithm="ramcom",
            environment=environment,
            metrics=summary_metrics,
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
                "random_seed": self._random_seed,
                "batch_size": self._batch_size,
                "config": {
                    "local_payment_ratio_zeta": self._local_payment_ratio_zeta,
                    "cross_platform_sharing_rate_mu2": self._cross_platform_sharing_rate_mu2,
                    "max_outer_payment_ratio": self._max_outer_payment_ratio,
                },
                "ramcom_config": {
                    "theta": metrics.get("theta"),
                    "k": metrics.get("k"),
                    "threshold": metrics.get("threshold"),
                    "max_fare": metrics.get("max_fare"),
                    "acceptance_model": metrics.get("acceptance_model"),
                    "payment_search": metrics.get("payment_search"),
                },
                "decision_trace": decision_trace,
            },
        )
        if output_dir is not None:
            output_dir.mkdir(parents=True, exist_ok=True)
            with (output_dir / "summary.json").open("w", encoding="utf-8") as handle:
                json.dump(summary, handle, indent=2)
        return summary


def build_ramcom_runner(
    batch_size: int = DEFAULT_CAPA_BATCH_SIZE,
    random_seed: int = DEFAULT_RAMCOM_RANDOM_SEED,
    local_payment_ratio_zeta: float = DEFAULT_LOCAL_PAYMENT_RATIO_ZETA,
    cross_platform_sharing_rate_mu2: float = DEFAULT_CROSS_PLATFORM_SHARING_RATE_MU2,
    max_outer_payment_ratio: float = DEFAULT_RAMCOM_MAX_OUTER_PAYMENT_RATIO,
    baseline_runner: Callable[..., dict[str, Any]] | None = None,
) -> RamCOMAlgorithmRunner:
    """Build the unified RamCOM runner."""
    return RamCOMAlgorithmRunner(
        batch_size=batch_size,
        random_seed=random_seed,
        local_payment_ratio_zeta=local_payment_ratio_zeta,
        cross_platform_sharing_rate_mu2=cross_platform_sharing_rate_mu2,
        max_outer_payment_ratio=max_outer_payment_ratio,
        baseline_runner=baseline_runner,
    )
