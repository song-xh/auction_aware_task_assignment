"""Unified RamCOM strategy wrapper for the algorithm registry."""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Any, Callable, Mapping

from baselines.ramcom import run_ramcom_baseline_environment
from capa.config import DEFAULT_RAMCOM_RANDOM_SEED

from .base import AlgorithmRunner
from .summary_utils import build_algorithm_summary


class RamCOMAlgorithmRunner(AlgorithmRunner):
    """Run the Chengdu-adapted RamCOM baseline through the unified environment interface."""

    def __init__(
        self,
        random_seed: int = DEFAULT_RAMCOM_RANDOM_SEED,
        baseline_runner: Callable[..., dict[str, Any]] | None = None,
    ) -> None:
        """Store the random seed and optional injected RamCOM baseline runner."""
        self._random_seed = random_seed
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
            progress_callback=progress_callback,
        )
        finished_at = datetime.now().astimezone()
        summary = build_algorithm_summary(
            algorithm="ramcom",
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
            extra_fields={"random_seed": self._random_seed},
        )
        if output_dir is not None:
            output_dir.mkdir(parents=True, exist_ok=True)
            with (output_dir / "summary.json").open("w", encoding="utf-8") as handle:
                json.dump(summary, handle, indent=2)
        return summary


def build_ramcom_runner(
    random_seed: int = DEFAULT_RAMCOM_RANDOM_SEED,
    baseline_runner: Callable[..., dict[str, Any]] | None = None,
) -> RamCOMAlgorithmRunner:
    """Build the unified RamCOM runner."""
    return RamCOMAlgorithmRunner(random_seed=random_seed, baseline_runner=baseline_runner)
