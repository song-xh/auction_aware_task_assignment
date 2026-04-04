"""Batch-level pre-computed distance matrix for active-node sets."""

from __future__ import annotations

from typing import Any, Hashable, Iterable


class BatchDistanceMatrix:
    """Pre-compute all-pairs distances for a small active-node set.

    Wraps an underlying travel model.  Lookups that hit the pre-computed
    matrix return instantly; misses fall through to the underlying model
    (which typically has its own LRU cache).

    Typical usage inside the batch runner::

        nodes = collect_active_nodes(couriers, parcels)
        bdm = BatchDistanceMatrix(travel_model)
        bdm.precompute(nodes)
        # use bdm.distance / bdm.travel_time instead of travel_model
    """

    def __init__(self, travel_model: Any) -> None:
        self._travel_model = travel_model
        self._matrix: dict[tuple[Hashable, Hashable], float] = {}
        self._speed: float | None = getattr(travel_model, 'speed', None) or getattr(travel_model, '_speed', None)

    # ------------------------------------------------------------------
    # Pre-computation
    # ------------------------------------------------------------------

    def precompute(self, nodes: Iterable[Hashable]) -> None:
        """Compute all-pairs distances for *nodes* via the underlying model.

        Only pairs not already cached are queried.  Self-distances are
        stored as ``0.0`` without a model call.
        """
        node_list = list(dict.fromkeys(nodes))  # deduplicate, preserve order
        for i, a in enumerate(node_list):
            for b in node_list[i:]:
                if a == b:
                    self._matrix[(a, b)] = 0.0
                    continue
                if (a, b) in self._matrix:
                    continue
                try:
                    d = float(self._travel_model.distance(a, b))
                except (KeyError, ValueError):
                    continue
                self._matrix[(a, b)] = d
                self._matrix[(b, a)] = d

    # ------------------------------------------------------------------
    # Public interface (same as DistanceMatrixTravelModel / TimedTravelModel)
    # ------------------------------------------------------------------

    def distance(self, start: Hashable, end: Hashable) -> float:
        """Return pre-computed distance, falling back to the underlying model."""
        if start == end:
            return 0.0
        cached = self._matrix.get((start, end))
        if cached is not None:
            return cached
        d = float(self._travel_model.distance(start, end))
        self._matrix[(start, end)] = d
        self._matrix[(end, start)] = d
        return d

    def travel_time(self, start: Hashable, end: Hashable) -> float:
        """Return travel time derived from pre-computed distance."""
        return self._travel_model.travel_time(start, end)

    @property
    def hits(self) -> int:
        """Number of entries currently in the matrix (for diagnostics)."""
        return len(self._matrix)
