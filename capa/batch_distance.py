"""Directed distance caches for insertion-heavy assignment rounds."""

from __future__ import annotations

from typing import Any, Hashable, Iterable, Sequence


class PersistentDirectedDistanceCache:
    """Cache exact directed shortest-path distances across matching rounds.

    The Chengdu road graph is static during one experiment run, so an exact
    directed distance remains valid across batches and retry rounds. This cache
    sits underneath per-round timing wrappers and batch-local warming.
    """

    def __init__(self, travel_model: Any) -> None:
        """Store the wrapped travel model and infer its travel speed if present."""

        self._travel_model = travel_model
        self._distances: dict[tuple[Hashable, Hashable], float] = {}
        self._speed: float | None = (
            getattr(travel_model, "speed", None)
            or getattr(travel_model, "_speed", None)
            or getattr(getattr(travel_model, "_travel_model", None), "speed", None)
            or getattr(getattr(travel_model, "_travel_model", None), "_speed", None)
        )

    def distance(self, start: Hashable, end: Hashable) -> float:
        """Return the cached exact directed distance between two locations."""

        if start == end:
            return 0.0
        cached = self._distances.get((start, end))
        if cached is not None:
            return cached
        value = float(self._travel_model.distance(start, end))
        self._distances[(start, end)] = value
        return value

    def travel_time(self, start: Hashable, end: Hashable) -> float:
        """Return travel time derived from the cached exact distance."""

        if self._speed is not None and self._speed > 0:
            return self.distance(start, end) / float(self._speed)
        return float(self._travel_model.travel_time(start, end))

    def precompute_pairs(self, pairs: Iterable[tuple[Hashable, Hashable]]) -> None:
        """Warm the persistent cache for the provided directed location pairs."""

        for start, end in dict.fromkeys(pairs):
            if start == end:
                self._distances[(start, end)] = 0.0
                continue
            if (start, end) not in self._distances:
                self._distances[(start, end)] = float(self._travel_model.distance(start, end))

    @property
    def hits(self) -> int:
        """Return the number of cached directed distance entries."""

        return len(self._distances)


class BatchDistanceMatrix:
    """Cache directed shortest-path lengths for one batch decision epoch.

    The cache is designed around insertion search rather than generic all-pairs
    graph closure. Callers may still precompute a full directed node set with
    `precompute()`, but the main fast path is `precompute_for_insertions()`,
    which warms only the route-segment and parcel-node pairs that local/cross
    insertion search will query in this epoch.
    """

    def __init__(self, travel_model: Any) -> None:
        self._travel_model = travel_model
        self._matrix: dict[tuple[Hashable, Hashable], float] = {}
        self._speed: float | None = (
            getattr(travel_model, "speed", None)
            or getattr(travel_model, "_speed", None)
            or getattr(getattr(travel_model, "_travel_model", None), "speed", None)
            or getattr(getattr(travel_model, "_travel_model", None), "_speed", None)
        )

    # ------------------------------------------------------------------
    # Pre-computation
    # ------------------------------------------------------------------

    def precompute(self, nodes: Iterable[Hashable]) -> None:
        """Compute directed distances for every ordered pair in *nodes*."""
        node_list = list(dict.fromkeys(nodes))
        pairs: list[tuple[Hashable, Hashable]] = []
        for start in node_list:
            for end in node_list:
                if start == end:
                    continue
                pairs.append((start, end))
        self.precompute_pairs(pairs)

    def precompute_pairs(self, pairs: Iterable[tuple[Hashable, Hashable]]) -> None:
        """Compute only the provided directed pairs via the underlying model."""
        for start, end in dict.fromkeys(pairs):
            if start == end:
                self._matrix[(start, end)] = 0.0
                continue
            if (start, end) in self._matrix:
                continue
            try:
                self._matrix[(start, end)] = float(self._travel_model.distance(start, end))
            except (KeyError, ValueError):
                continue

    def precompute_for_insertions(self, couriers: Sequence[Any], parcels: Sequence[Any]) -> None:
        """Warm only the directed pairs required by route insertion search.

        For each courier route segment `(start, end)`, insertion search needs:
        - the base segment distance `start -> end`
        - the detour prefix `start -> parcel`
        - the detour suffix `parcel -> end`
        """
        self.precompute_for_candidate_pairs(
            (courier, parcel)
            for courier in couriers
            for parcel in parcels
        )

    def precompute_for_candidate_pairs(self, candidate_pairs: Iterable[tuple[Any, Any]]) -> None:
        """Warm only the directed pairs required by explicit courier-parcel candidates."""

        parcel_locations_by_courier: dict[Hashable, tuple[Any, dict[Hashable, None]]] = {}
        pairs: list[tuple[Hashable, Hashable]] = []
        for courier, parcel in candidate_pairs:
            courier_key = getattr(courier, "courier_id", id(courier))
            parcel_location = getattr(parcel, "location")
            if courier_key not in parcel_locations_by_courier:
                parcel_locations_by_courier[courier_key] = (courier, {})
            parcel_locations_by_courier[courier_key][1][parcel_location] = None
        for courier, parcel_locations in parcel_locations_by_courier.values():
            route_nodes = [
                getattr(courier, "current_location"),
                *list(getattr(courier, "route_locations", [])),
                getattr(courier, "depot_location"),
            ]
            for index in range(len(route_nodes) - 1):
                start = route_nodes[index]
                end = route_nodes[index + 1]
                pairs.append((start, end))
                for parcel_location in parcel_locations.keys():
                    pairs.append((start, parcel_location))
                    pairs.append((parcel_location, end))
        self.precompute_pairs(pairs)

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
        return d

    def travel_time(self, start: Hashable, end: Hashable) -> float:
        """Return travel time derived from pre-computed distance."""
        if self._speed is not None and self._speed > 0:
            return self.distance(start, end) / float(self._speed)
        return self._travel_model.travel_time(start, end)

    @property
    def hits(self) -> int:
        """Number of entries currently in the matrix (for diagnostics)."""
        return len(self._matrix)
