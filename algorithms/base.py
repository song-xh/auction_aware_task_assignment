"""Shared contracts for unified algorithm runner entrypoints."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable, Mapping


class AlgorithmRunner(ABC):
    """Define the minimal interface that all unified algorithm runners must expose."""

    @abstractmethod
    def run(
        self,
        environment: Any,
        output_dir: Path | None = None,
        progress_callback: Callable[[Mapping[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        """Execute one algorithm against a prepared environment and return a summary."""


class UnavailableAlgorithmRunner(AlgorithmRunner):
    """Represent a registered algorithm whose runnable implementation is not wired yet."""

    def __init__(self, algorithm_name: str, reason: str) -> None:
        """Store the algorithm name and the explicit failure reason."""
        self._algorithm_name = algorithm_name
        self._reason = reason

    def run(
        self,
        environment: Any,
        output_dir: Path | None = None,
        progress_callback: Callable[[Mapping[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        """Raise an explicit error instead of silently falling back to another algorithm."""
        del environment
        del output_dir
        del progress_callback
        raise NotImplementedError(f"{self._algorithm_name} is not implemented yet: {self._reason}")
