"""Shared fake travel and geo helpers for CAPA unit tests."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FakeTravelModel:
    """Minimal directed travel model with call counting."""

    distances: dict[tuple[object, object], float]
    speed: float = 1.0

    def __post_init__(self) -> None:
        self.distance_calls: list[tuple[object, object]] = []
        self.travel_time_calls: list[tuple[object, object]] = []

    def distance(self, start: object, end: object) -> float:
        """Return the exact directed distance and record the call."""

        self.distance_calls.append((start, end))
        if start == end:
            return 0.0
        return float(self.distances[(start, end)])

    def travel_time(self, start: object, end: object) -> float:
        """Return the travel time derived from the directed distance."""

        self.travel_time_calls.append((start, end))
        return self.distance(start, end) / self.speed


@dataclass
class FakeGeoIndex:
    """Minimal geo lower-bound index with deterministic answers."""

    lower_bounds: dict[tuple[object, object], float]

    def haversine_meters_between(self, start: object, end: object) -> float | None:
        """Return the configured lower bound for the directed pair."""

        if start == end:
            return 0.0
        return self.lower_bounds.get((start, end), self.lower_bounds.get((end, start)))
