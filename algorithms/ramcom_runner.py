"""Unified RamCOM strategy wrapper for the algorithm registry."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from baselines.ramcom import run_ramcom_baseline_environment

from .base import AlgorithmRunner


class RamCOMAlgorithmRunner(AlgorithmRunner):
    """Run the Chengdu-adapted RamCOM baseline through the unified environment interface."""

    def __init__(
        self,
        random_seed: int = 1,
        baseline_runner: Callable[..., dict[str, float]] | None = None,
    ) -> None:
        """Store the random seed and optional injected RamCOM baseline runner."""
        self._random_seed = random_seed
        self._baseline_runner = baseline_runner or run_ramcom_baseline_environment

    def run(self, environment: Any, output_dir: Path | None = None) -> dict[str, Any]:
        """Execute RamCOM against a prepared Chengdu environment and return a summary."""
        metrics = self._baseline_runner(
            environment=environment,
            random_seed=self._random_seed,
        )
        summary = {
            "algorithm": "ramcom",
            "random_seed": self._random_seed,
            "metrics": metrics,
        }
        if output_dir is not None:
            output_dir.mkdir(parents=True, exist_ok=True)
            with (output_dir / "summary.json").open("w", encoding="utf-8") as handle:
                json.dump(summary, handle, indent=2)
        return summary


def build_ramcom_runner(
    random_seed: int = 1,
    baseline_runner: Callable[..., dict[str, float]] | None = None,
) -> RamCOMAlgorithmRunner:
    """Build the unified RamCOM runner."""
    return RamCOMAlgorithmRunner(random_seed=random_seed, baseline_runner=baseline_runner)
