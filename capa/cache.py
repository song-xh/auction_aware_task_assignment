"""Reusable cache primitives for CAPA route evaluation hot paths."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Hashable, Tuple

from .models import Courier


RouteSignature = tuple[Hashable, ...]
InsertionResult = tuple[float, int]


def build_courier_route_signature(courier: Courier) -> RouteSignature:
    """Build a stable route signature for one courier snapshot.

    Args:
        courier: CAPA courier snapshot.

    Returns:
        A hashable signature capturing the route geometry relevant to insertion
        search and detour computation.
    """

    return (
        courier.current_location,
        *courier.route_locations,
        courier.depot_location,
    )


@dataclass
class InsertionCache:
    """Cache best insertion results for repeated courier-route and parcel pairs."""

    _entries: Dict[tuple[str, RouteSignature, Hashable], InsertionResult] = field(default_factory=dict)

    def get(self, courier: Courier, parcel_location: Hashable) -> InsertionResult | None:
        """Return a cached insertion result for one courier-route and parcel pair.

        Args:
            courier: CAPA courier snapshot.
            parcel_location: Parcel location identifier.

        Returns:
            The cached `(best_ratio, best_index)` pair, or `None` if absent.
        """

        return self._entries.get(self._build_key(courier, parcel_location))

    def store(self, courier: Courier, parcel_location: Hashable, result: InsertionResult) -> None:
        """Store an insertion result for one courier-route and parcel pair.

        Args:
            courier: CAPA courier snapshot.
            parcel_location: Parcel location identifier.
            result: `(best_ratio, best_index)` returned by insertion search.
        """

        self._entries[self._build_key(courier, parcel_location)] = result

    def clear(self) -> None:
        """Drop all cached insertion entries."""

        self._entries.clear()

    def _build_key(self, courier: Courier, parcel_location: Hashable) -> tuple[str, RouteSignature, Hashable]:
        """Build the internal cache key for one insertion lookup."""

        return (
            courier.courier_id,
            build_courier_route_signature(courier),
            parcel_location,
        )
