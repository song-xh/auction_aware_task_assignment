"""Unified BaseGTA strategy wrapper for the algorithm registry."""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Any, Callable, Mapping

from baselines.gta import run_basegta_baseline_environment
from capa.config import (
    DEFAULT_CROSS_PLATFORM_SHARING_RATE_MU2,
    DEFAULT_LOCAL_PAYMENT_RATIO_ZETA,
)

from .base import AlgorithmRunner
from .summary_utils import build_algorithm_summary


class BaseGTARunner(AlgorithmRunner):
    """Run BaseGTA through the unified environment interface."""

    def __init__(
        self,
        local_payment_ratio_zeta: float = DEFAULT_LOCAL_PAYMENT_RATIO_ZETA,
        cross_platform_sharing_rate_mu2: float = DEFAULT_CROSS_PLATFORM_SHARING_RATE_MU2,
        baseline_runner: Callable[..., dict[str, Any]] | None = None,
    ) -> None:
        """Store revenue parameters and the optional injected baseline runner."""
        self._local_payment_ratio_zeta = float(local_payment_ratio_zeta)
        self._cross_platform_sharing_rate_mu2 = float(cross_platform_sharing_rate_mu2)
        self._baseline_runner = baseline_runner or run_basegta_baseline_environment

    def run(
        self,
        environment: Any,
        output_dir: Path | None = None,
        progress_callback: Callable[[Mapping[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        """Execute BaseGTA against a prepared Chengdu environment and return a summary."""
        started_at = datetime.now().astimezone()
        metrics = self._baseline_runner(
            environment=environment,
            local_payment_ratio=self._local_payment_ratio_zeta,
            cross_platform_sharing_rate_mu2=self._cross_platform_sharing_rate_mu2,
            progress_callback=progress_callback,
        )
        finished_at = datetime.now().astimezone()
        summary = build_algorithm_summary(
            algorithm="basegta",
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
                "config": {
                    "local_payment_ratio_zeta": self._local_payment_ratio_zeta,
                    "cross_platform_sharing_rate_mu2": self._cross_platform_sharing_rate_mu2,
                },
            },
        )
        if output_dir is not None:
            output_dir.mkdir(parents=True, exist_ok=True)
            with (output_dir / "summary.json").open("w", encoding="utf-8") as handle:
                json.dump(summary, handle, indent=2)
        return summary


def build_basegta_runner(
    local_payment_ratio_zeta: float = DEFAULT_LOCAL_PAYMENT_RATIO_ZETA,
    cross_platform_sharing_rate_mu2: float = DEFAULT_CROSS_PLATFORM_SHARING_RATE_MU2,
    baseline_runner: Callable[..., dict[str, Any]] | None = None,
) -> BaseGTARunner:
    """Build the unified BaseGTA runner."""
    return BaseGTARunner(
        local_payment_ratio_zeta=local_payment_ratio_zeta,
        cross_platform_sharing_rate_mu2=cross_platform_sharing_rate_mu2,
        baseline_runner=baseline_runner,
    )
