"""Reusable cache primitives for CAPA route evaluation hot paths."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Hashable, Iterable, Tuple

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
    _keys_by_courier: Dict[str, set[tuple[str, RouteSignature, Hashable]]] = field(default_factory=dict)

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

        key = self._build_key(courier, parcel_location)
        self._entries[key] = result
        self._keys_by_courier.setdefault(courier.courier_id, set()).add(key)

    def clear(self) -> None:
        """Drop all cached insertion entries."""

        self._entries.clear()
        self._keys_by_courier.clear()

    def invalidate_courier(self, courier_id: str) -> None:
        """Drop all cached insertion entries associated with one courier.

        Args:
            courier_id: Stable courier identifier used in CAPA snapshots.
        """

        keys = self._keys_by_courier.pop(courier_id, set())
        for key in keys:
            self._entries.pop(key, None)

    def prune_to_active_routes(self, couriers: Iterable[Courier]) -> None:
        """Keep only cache entries matching the couriers' current route signatures.

        Args:
            couriers: Current CAPA courier snapshots for the active decision epoch.
        """

        active_signatures = {
            courier.courier_id: build_courier_route_signature(courier)
            for courier in couriers
        }
        active_courier_ids = set(active_signatures)
        stale_couriers = set(self._keys_by_courier) - active_courier_ids
        for courier_id in stale_couriers:
            self.invalidate_courier(courier_id)
        for courier_id, keys in list(self._keys_by_courier.items()):
            current_signature = active_signatures.get(courier_id)
            if current_signature is None:
                continue
            stale_keys = {key for key in keys if key[1] != current_signature}
            for key in stale_keys:
                self._entries.pop(key, None)
            if stale_keys:
                remaining = keys - stale_keys
                if remaining:
                    self._keys_by_courier[courier_id] = remaining
                else:
                    self._keys_by_courier.pop(courier_id, None)

    def _build_key(self, courier: Courier, parcel_location: Hashable) -> tuple[str, RouteSignature, Hashable]:
        """Build the internal cache key for one insertion lookup."""

        return (
            courier.courier_id,
            build_courier_route_signature(courier),
            parcel_location,
        )
