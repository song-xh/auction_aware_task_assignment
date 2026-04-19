"""Shared CAPA helpers for travel, cache, timing, geometry, revenue, and insertion utility."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Dict, Hashable, Iterable, List, Mapping, Sequence, Tuple

from .config import DEFAULT_LOCAL_PAYMENT_RATIO_ZETA
from .models import BatchTimingBreakdown, CAPAConfig, Courier, Parcel, UtilityEvaluation


DEFAULT_LOCAL_PAYMENT_RATIO = DEFAULT_LOCAL_PAYMENT_RATIO_ZETA


# 几何下界工具：用于在不触发路网最短路的前提下做 cheap filter。
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
    """Map node IDs to `(lat, lng)` for O(1) geometric lookups."""

    def __init__(self, nmap: Mapping[str, Any] | None = None) -> None:
        """Build the geo index from a Chengdu graph node map when available."""

        self._coords: dict[str, tuple[float, float]] = {}
        if nmap is not None:
            for node_id, node in nmap.items():
                self._coords[str(node_id)] = (float(node.lat), float(node.lng))

    def get(self, node_id: Hashable) -> tuple[float, float] | None:
        """Return `(lat, lng)` for one node ID, or `None` if unknown."""

        return self._coords.get(str(node_id))

    def haversine_meters_between(self, a: Hashable, b: Hashable) -> float | None:
        """Return the Haversine lower-bound distance between two node IDs."""

        ca = self.get(a)
        cb = self.get(b)
        if ca is None or cb is None:
            return None
        return haversine_meters(ca[0], ca[1], cb[0], cb[1])

    def __len__(self) -> int:
        """Return the number of indexed nodes."""

        return len(self._coords)


# 路由插入缓存：避免同一 courier-route / parcel 重复做精确插入搜索。
RouteSignature = tuple[Hashable, ...]
InsertionResult = tuple[float, int]


def build_courier_route_signature(courier: Courier) -> RouteSignature:
    """Build a stable route signature for one courier snapshot."""

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
        """Return a cached insertion result for one courier-route and parcel pair."""

        return self._entries.get(self._build_key(courier, parcel_location))

    def store(self, courier: Courier, parcel_location: Hashable, result: InsertionResult) -> None:
        """Store one insertion result for a courier-route and parcel pair."""

        key = self._build_key(courier, parcel_location)
        self._entries[key] = result
        self._keys_by_courier.setdefault(courier.courier_id, set()).add(key)

    def clear(self) -> None:
        """Drop all cached insertion entries."""

        self._entries.clear()
        self._keys_by_courier.clear()

    def invalidate_courier(self, courier_id: str) -> None:
        """Drop all cached insertion entries associated with one courier."""

        keys = self._keys_by_courier.pop(courier_id, set())
        for key in keys:
            self._entries.pop(key, None)

    def prune_to_active_routes(self, couriers: Iterable[Courier]) -> None:
        """Keep only cache entries matching the couriers' current route signatures."""

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


# timing 工具：把 routing / insertion / movement 的开销拆开记录。
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


# 批量距离缓存：针对 insertion-heavy 回合做 directed pair warmup。
class PersistentDirectedDistanceCache:
    """Cache exact directed shortest-path distances across matching rounds."""

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
    """Cache directed shortest-path lengths for one batch decision epoch."""

    def __init__(self, travel_model: Any) -> None:
        """Store the wrapped travel model and its inferred speed if available."""

        self._travel_model = travel_model
        self._matrix: dict[tuple[Hashable, Hashable], float] = {}
        self._speed: float | None = (
            getattr(travel_model, "speed", None)
            or getattr(travel_model, "_speed", None)
            or getattr(getattr(travel_model, "_travel_model", None), "speed", None)
            or getattr(getattr(travel_model, "_travel_model", None), "_speed", None)
        )

    def precompute(self, nodes: Iterable[Hashable]) -> None:
        """Compute directed distances for every ordered pair in `nodes`."""

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
        """Warm only the directed pairs required by route insertion search."""

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

    def distance(self, start: Hashable, end: Hashable) -> float:
        """Return pre-computed distance, falling back to the underlying model."""

        if start == end:
            return 0.0
        cached = self._matrix.get((start, end))
        if cached is not None:
            return cached
        distance_value = float(self._travel_model.distance(start, end))
        self._matrix[(start, end)] = distance_value
        return distance_value

    def travel_time(self, start: Hashable, end: Hashable) -> float:
        """Return travel time derived from the pre-computed distance."""

        if self._speed is not None and self._speed > 0:
            return self.distance(start, end) / float(self._speed)
        return self._travel_model.travel_time(start, end)

    @property
    def hits(self) -> int:
        """Return the number of entries currently cached in the batch matrix."""

        return len(self._matrix)


# travel / revenue 工具：测试 travel model 与平台收益计算。
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


def compute_local_courier_payment(parcel_fare: float, local_payment_ratio: float = DEFAULT_LOCAL_PAYMENT_RATIO) -> float:
    """Return the fixed local-courier payment `Rc(tau, c) = zeta * p_tau`."""

    return float(local_payment_ratio) * float(parcel_fare)


def compute_local_platform_revenue_for_local_completion(
    parcel_fare: float,
    local_payment_ratio: float = DEFAULT_LOCAL_PAYMENT_RATIO,
) -> float:
    """Return local-platform revenue for an inner-courier completion."""

    return float(parcel_fare) - compute_local_courier_payment(parcel_fare, local_payment_ratio)


def compute_local_platform_revenue_for_cross_completion(parcel_fare: float, platform_payment: float) -> float:
    """Return local-platform revenue for a cross-platform completion."""

    return float(parcel_fare) - float(platform_payment)


def compute_cooperating_platform_revenue(platform_payment: float, courier_payment: float) -> float:
    """Return the cooperating platform's retained profit."""

    return float(platform_payment) - float(courier_payment)


# CAPA 计算工具：保留 Eq.(1)/(6)/(7) 与插入搜索的公共实现。
def build_route_nodes(courier: Courier) -> List[object]:
    """Build the courier route as current location, pending route, and final depot."""

    return [courier.current_location, *courier.route_locations, courier.depot_location]


def calculate_capacity_ratio(parcel: Parcel, courier: Courier) -> float:
    """Compute the Eq.6 capacity ratio for a courier-parcel pair."""

    if courier.capacity <= 0:
        raise ValueError("Courier capacity must be positive.")
    return 1.0 - ((courier.current_load + parcel.weight) / courier.capacity)


def find_best_local_insertion(
    parcel: Parcel,
    courier: Courier,
    travel_model: DistanceMatrixTravelModel,
    timing: TimingAccumulator | None = None,
    insertion_cache: InsertionCache | None = None,
    geo_index: GeoIndex | None = None,
) -> Tuple[float, int]:
    """Return the best insertion index and the Eq.6 detour ratio for local matching."""

    if insertion_cache is not None:
        cached = insertion_cache.get(courier, parcel.location)
        if cached is not None:
            return cached
    started = perf_counter()
    if timing is not None:
        timing.begin_insertion()
    route_nodes = build_route_nodes(courier)
    best_ratio = float("-inf")
    best_index = 0
    try:
        for index in range(len(route_nodes) - 1):
            start = route_nodes[index]
            end = route_nodes[index + 1]
            base_distance = travel_model.distance(start, end)
            if geo_index is not None and best_ratio > float("-inf"):
                lower_bound_start = geo_index.haversine_meters_between(start, parcel.location)
                lower_bound_end = geo_index.haversine_meters_between(parcel.location, end)
                if lower_bound_start is not None and lower_bound_end is not None:
                    lower_bound_detour = lower_bound_start + lower_bound_end
                    if lower_bound_detour > 0:
                        upper_bound_ratio = base_distance / lower_bound_detour
                        if upper_bound_ratio <= best_ratio:
                            continue
            detour_distance = travel_model.distance(start, parcel.location) + travel_model.distance(parcel.location, end)
            if detour_distance <= 0:
                ratio = 1.0
            else:
                ratio = base_distance / detour_distance
            if ratio > best_ratio:
                best_ratio = ratio
                best_index = index
        result = (best_ratio, best_index)
        if insertion_cache is not None:
            insertion_cache.store(courier, parcel.location, result)
        return result
    finally:
        if timing is not None:
            timing.end_insertion()
            timing.insertion_time_seconds += perf_counter() - started


def find_best_auction_detour_ratio(
    parcel: Parcel,
    courier: Courier,
    travel_model: DistanceMatrixTravelModel,
    timing: TimingAccumulator | None = None,
    insertion_cache: InsertionCache | None = None,
    geo_index: GeoIndex | None = None,
) -> float:
    """Return the Eq.1 detour term used by the FPSA bid function."""

    local_ratio, _ = find_best_local_insertion(
        parcel,
        courier,
        travel_model,
        timing=timing,
        insertion_cache=insertion_cache,
        geo_index=geo_index,
    )
    return 1.0 - local_ratio


def calculate_utility(
    parcel: Parcel,
    courier: Courier,
    travel_model: DistanceMatrixTravelModel,
    config: CAPAConfig,
    timing: TimingAccumulator | None = None,
    insertion_cache: InsertionCache | None = None,
    geo_index: GeoIndex | None = None,
) -> UtilityEvaluation:
    """Compute the Eq.6 utility and preserve the best insertion index."""

    detour_ratio, insertion_index = find_best_local_insertion(
        parcel,
        courier,
        travel_model,
        timing=timing,
        insertion_cache=insertion_cache,
        geo_index=geo_index,
    )
    capacity_ratio = calculate_capacity_ratio(parcel, courier)
    utility_value = (
        config.utility_balance_gamma * capacity_ratio
        + (1.0 - config.utility_balance_gamma) * detour_ratio
    )
    return UtilityEvaluation(
        value=utility_value,
        capacity_ratio=capacity_ratio,
        detour_ratio=detour_ratio,
        insertion_index=insertion_index,
    )


def calculate_threshold(utility_values: Iterable[float], omega: float) -> float:
    """Compute the Eq.7 threshold over the entire set of feasible pairs `M_t`."""

    values = list(utility_values)
    if not values:
        return float("inf")
    return omega * (sum(values) / len(values))
