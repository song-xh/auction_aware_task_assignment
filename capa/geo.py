"""Geometric lower-bound helpers for cheap feasibility pre-filtering."""

from __future__ import annotations

import math
from typing import Any, Hashable, Mapping

EARTH_RADIUS_KM = 6378.137


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Return the Haversine great-circle distance in kilometres."""
    rlat1 = math.radians(lat1)
    rlat2 = math.radians(lat2)
    dlat = rlat1 - rlat2
    dlng = math.radians(lng1) - math.radians(lng2)
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlng / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def haversine_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Return the Haversine great-circle distance in metres."""
    return haversine_km(lat1, lng1, lat2, lng2) * 1000.0


class GeoIndex:
    """Map node IDs to (lat, lng) for O(1) geometric lookups.

    Constructed once from the Chengdu graph ``nMap`` and reused across
    the entire simulation run.
    """

    def __init__(self, nmap: Mapping[str, Any] | None = None) -> None:
        self._coords: dict[str, tuple[float, float]] = {}
        if nmap is not None:
            for node_id, node in nmap.items():
                self._coords[str(node_id)] = (float(node.lat), float(node.lng))

    def get(self, node_id: Hashable) -> tuple[float, float] | None:
        """Return ``(lat, lng)`` for *node_id*, or ``None`` if unknown."""
        return self._coords.get(str(node_id))

    def haversine_meters_between(self, a: Hashable, b: Hashable) -> float | None:
        """Return the Haversine lower-bound distance between two node IDs.

        Returns ``None`` if either node is not in the index (caller should
        fall back to exact distance).
        """
        ca = self.get(a)
        cb = self.get(b)
        if ca is None or cb is None:
            return None
        return haversine_meters(ca[0], ca[1], cb[0], cb[1])

    def __len__(self) -> int:
        return len(self._coords)
