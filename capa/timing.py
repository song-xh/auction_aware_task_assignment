"""Shared timing breakdown models used by CAPA metrics and experiment outputs."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any


@dataclass(frozen=True)
class BatchTimingBreakdown:
    """Record decision and excluded timing components for one matching round."""

    decision_time_seconds: float = 0.0
    routing_time_seconds: float = 0.0
    insertion_time_seconds: float = 0.0
    movement_time_seconds: float = 0.0


@dataclass
class TimingAccumulator:
    """Collect mutable timing counters before freezing them into one batch report."""

    decision_time_seconds: float = 0.0
    routing_time_seconds: float = 0.0
    insertion_time_seconds: float = 0.0
    movement_time_seconds: float = 0.0
    _inside_insertion: int = 0

    def freeze(self) -> BatchTimingBreakdown:
        """Convert the mutable accumulator into an immutable batch breakdown."""
        return BatchTimingBreakdown(
            decision_time_seconds=self.decision_time_seconds,
            routing_time_seconds=self.routing_time_seconds,
            insertion_time_seconds=self.insertion_time_seconds,
            movement_time_seconds=self.movement_time_seconds,
        )

    def begin_insertion(self) -> None:
        """Mark entry into insertion-search timing so nested routing is not double-counted."""
        self._inside_insertion += 1

    def end_insertion(self) -> None:
        """Mark exit from insertion-search timing."""
        self._inside_insertion = max(0, self._inside_insertion - 1)

    @property
    def inside_insertion(self) -> bool:
        """Return whether timing is currently inside an insertion-search region."""
        return self._inside_insertion > 0


class TimedTravelModel:
    """Wrap a travel model and accumulate routing-query cost outside insertion timing."""

    def __init__(self, travel_model: Any, timing: TimingAccumulator | None) -> None:
        """Store the wrapped travel model and mutable timing accumulator."""
        self._travel_model = travel_model
        self._timing = timing

    def distance(self, start: Any, end: Any) -> float:
        """Return wrapped shortest-path distance while accumulating routing time."""
        started = perf_counter()
        value = self._travel_model.distance(start, end)
        elapsed = perf_counter() - started
        if self._timing is not None and not self._timing.inside_insertion:
            self._timing.routing_time_seconds += elapsed
        return value

    def travel_time(self, start: Any, end: Any) -> float:
        """Return wrapped shortest-path travel time while accumulating routing time."""
        started = perf_counter()
        value = self._travel_model.travel_time(start, end)
        elapsed = perf_counter() - started
        if self._timing is not None and not self._timing.inside_insertion:
            self._timing.routing_time_seconds += elapsed
        return value
