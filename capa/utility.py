"""Utility and detour helpers for CAMA and DAPA."""

from __future__ import annotations

from typing import Iterable, List, Tuple

from .models import CAPAConfig, Courier, Parcel, UtilityEvaluation
from .travel import DistanceMatrixTravelModel


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
) -> Tuple[float, int]:
    """Return the best insertion index and the Eq.6 detour ratio for local matching."""
    route_nodes = build_route_nodes(courier)
    best_ratio = float("-inf")
    best_index = 0
    for index in range(len(route_nodes) - 1):
        start = route_nodes[index]
        end = route_nodes[index + 1]
        base_distance = travel_model.distance(start, end)
        detour_distance = travel_model.distance(start, parcel.location) + travel_model.distance(parcel.location, end)
        if detour_distance <= 0:
            raise ValueError("Detour distance must be positive.")
        ratio = base_distance / detour_distance
        if ratio > best_ratio:
            best_ratio = ratio
            best_index = index
    return best_ratio, best_index


def find_best_auction_detour_ratio(
    parcel: Parcel,
    courier: Courier,
    travel_model: DistanceMatrixTravelModel,
) -> float:
    """Return the Eq.1 detour term used by the FPSA bid function."""
    local_ratio, _ = find_best_local_insertion(parcel, courier, travel_model)
    return 1.0 - local_ratio


def calculate_utility(
    parcel: Parcel,
    courier: Courier,
    travel_model: DistanceMatrixTravelModel,
    config: CAPAConfig,
) -> UtilityEvaluation:
    """Compute the Eq.6 utility and preserve the best insertion index."""
    detour_ratio, insertion_index = find_best_local_insertion(parcel, courier, travel_model)
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
