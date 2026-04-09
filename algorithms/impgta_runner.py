"""Unified ImpGTA strategy wrapper for the algorithm registry."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Mapping

from baselines.gta import run_impgta_baseline_environment
from capa.config import DEFAULT_IMPGTA_WINDOW_SECONDS

from .base import AlgorithmRunner


class ImpGTARunner(AlgorithmRunner):
    """Run ImpGTA through the unified environment interface."""

    def __init__(
        self,
        prediction_window_seconds: int = DEFAULT_IMPGTA_WINDOW_SECONDS,
        baseline_runner: Callable[..., dict[str, float]] | None = None,
    ) -> None:
        """Store the ImpGTA future window and optional injected baseline runner."""
        self._prediction_window_seconds = prediction_window_seconds
        self._baseline_runner = baseline_runner or run_impgta_baseline_environment

    def run(
        self,
        environment: Any,
        output_dir: Path | None = None,
        progress_callback: Callable[[Mapping[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        """Execute ImpGTA against a prepared Chengdu environment and return a summary."""
        metrics = self._baseline_runner(
            environment=environment,
            prediction_window_seconds=self._prediction_window_seconds,
            progress_callback=progress_callback,
        )
        summary = {
            "algorithm": "impgta",
            "prediction_window_seconds": self._prediction_window_seconds,
            "metrics": metrics,
        }
        if output_dir is not None:
            output_dir.mkdir(parents=True, exist_ok=True)
            with (output_dir / "summary.json").open("w", encoding="utf-8") as handle:
                json.dump(summary, handle, indent=2)
        return summary


def build_impgta_runner(
    prediction_window_seconds: int = DEFAULT_IMPGTA_WINDOW_SECONDS,
    baseline_runner: Callable[..., dict[str, float]] | None = None,
) -> ImpGTARunner:
    """Build the unified ImpGTA runner."""
    return ImpGTARunner(
        prediction_window_seconds=prediction_window_seconds,
        baseline_runner=baseline_runner,
    )
