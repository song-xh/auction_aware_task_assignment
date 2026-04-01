"""Travel-model abstractions used by the CAPA package."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Hashable, Mapping, Tuple


@dataclass(frozen=True)
class DistanceMatrixTravelModel:
    """Provide deterministic distance and travel-time lookups for tests and runners."""

    distances: Mapping[Tuple[Hashable, Hashable], float]
    speed: float = 1.0

    def distance(self, start: Hashable, end: Hashable) -> float:
        """Return the directed or symmetric distance between two locations."""
        if start == end:
            return 0.0
        direct = self.distances.get((start, end))
        if direct is not None:
            return float(direct)
        reverse = self.distances.get((end, start))
        if reverse is not None:
            return float(reverse)
        raise KeyError(f"Missing distance between {start!r} and {end!r}.")

    def travel_time(self, start: Hashable, end: Hashable) -> float:
        """Return travel time based on the stored distance matrix and scalar speed."""
        if self.speed <= 0:
            raise ValueError("Travel speed must be positive.")
        return self.distance(start, end) / self.speed
