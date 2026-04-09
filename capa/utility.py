"""Shared CAPA helpers for travel lookup, revenue accounting, and insertion utility."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Hashable, Iterable, List, Mapping, Tuple

from .cache import InsertionCache
from .config import DEFAULT_LOCAL_PAYMENT_RATIO_ZETA
from .geo import GeoIndex
from .models import CAPAConfig, Courier, Parcel, UtilityEvaluation
from .timing import TimingAccumulator


DEFAULT_LOCAL_PAYMENT_RATIO = DEFAULT_LOCAL_PAYMENT_RATIO_ZETA


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
    """Return the best insertion index and the Eq.6 detour ratio for local matching.

    Args:
        parcel: Candidate parcel.
        courier: Courier snapshot carrying the current route.
        travel_model: Exact directed travel model.
        timing: Optional timing accumulator.
        insertion_cache: Optional route-aware insertion cache.
        geo_index: Optional geometric index used only for safe lower-bound pruning.

    Returns:
        `(best_ratio, best_index)` for the exact best insertion position.
    """
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
    """Compute the Eq.7 threshold over the entire set of feasible pairs M_t."""
    values = list(utility_values)
    if not values:
        return float("inf")
    return omega * (sum(values) / len(values))
