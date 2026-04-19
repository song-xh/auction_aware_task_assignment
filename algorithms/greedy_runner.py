"""Unified Greedy strategy wrapper for the algorithm registry."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Mapping

from baselines.greedy import run_greedy_baseline_environment
from capa.config import DEFAULT_CAPA_BATCH_SIZE

from .base import AlgorithmRunner


class GreedyAlgorithmRunner(AlgorithmRunner):
    """Run the legacy Greedy baseline through the unified environment interface."""

    def __init__(
        self,
        batch_size: int = DEFAULT_CAPA_BATCH_SIZE,
        baseline_runner: Callable[..., dict[str, float]] | None = None,
    ) -> None:
        """Store the batch size and optional injected baseline runner."""
        self._batch_size = batch_size
        self._baseline_runner = baseline_runner or run_greedy_baseline_environment

    def run(
        self,
        environment: Any,
        output_dir: Path | None = None,
        progress_callback: Callable[[Mapping[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        """Execute Greedy against a prepared Chengdu environment and return a summary."""
        metrics = self._baseline_runner(
            environment=environment,
            batch_size=self._batch_size,
            progress_callback=progress_callback,
        )
        summary = {
            "algorithm": "greedy",
            "batch_size": self._batch_size,
            "metrics": metrics,
        }
        if output_dir is not None:
            output_dir.mkdir(parents=True, exist_ok=True)
            with (output_dir / "summary.json").open("w", encoding="utf-8") as handle:
                json.dump(summary, handle, indent=2)
        return summary


def build_greedy_runner(
    batch_size: int = DEFAULT_CAPA_BATCH_SIZE,
    baseline_runner: Callable[..., dict[str, float]] | None = None,
) -> GreedyAlgorithmRunner:
    """Build the unified Greedy runner."""
    return GreedyAlgorithmRunner(batch_size=batch_size, baseline_runner=baseline_runner)
