"""Unified BaseGTA strategy wrapper for the algorithm registry."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from baselines.gta import run_basegta_baseline_environment

from .base import AlgorithmRunner


class BaseGTARunner(AlgorithmRunner):
    """Run BaseGTA through the unified environment interface."""

    def __init__(self, baseline_runner: Callable[..., dict[str, float]] | None = None) -> None:
        """Store the optional injected baseline runner."""
        self._baseline_runner = baseline_runner or run_basegta_baseline_environment

    def run(self, environment: Any, output_dir: Path | None = None) -> dict[str, Any]:
        """Execute BaseGTA against a prepared Chengdu environment and return a summary."""
        metrics = self._baseline_runner(environment=environment)
        summary = {
            "algorithm": "basegta",
            "metrics": metrics,
        }
        if output_dir is not None:
            output_dir.mkdir(parents=True, exist_ok=True)
            with (output_dir / "summary.json").open("w", encoding="utf-8") as handle:
                json.dump(summary, handle, indent=2)
        return summary


def build_basegta_runner(
    baseline_runner: Callable[..., dict[str, float]] | None = None,
) -> BaseGTARunner:
    """Build the unified BaseGTA runner."""
    return BaseGTARunner(baseline_runner=baseline_runner)
