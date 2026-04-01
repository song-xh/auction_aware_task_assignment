"""Paper-faithful dual-layer auction implementation for Algorithm 3."""

from __future__ import annotations

from typing import List, Sequence

from .cama import is_courier_available
from .constraints import is_within_service_radius
from .models import (
    Assignment,
    CAPAConfig,
    CooperatingPlatform,
    Courier,
    DAPAResult,
    Parcel,
    PlatformBid,
)
from .travel import DistanceMatrixTravelModel
from .utility import find_best_auction_detour_ratio, find_best_local_insertion


def is_feasible_cross_match(
    parcel: Parcel,
    courier: Courier,
    travel_model: DistanceMatrixTravelModel,
    now: int,
    service_radius_meters: float | None = None,
) -> bool:
    """Check the validity condition required before a courier may enter FPSA."""
    if not is_courier_available(courier, now):
        return False
    if courier.current_load + parcel.weight > courier.capacity:
        return False
    if not is_within_service_radius(courier.current_location, parcel.location, travel_model, service_radius_meters):
        return False
    arrival_time = now + travel_model.travel_time(courier.current_location, parcel.location)
    return arrival_time <= parcel.deadline


def compute_fpsa_bid(
    parcel: Parcel,
    courier: Courier,
    platform: CooperatingPlatform,
    travel_model: DistanceMatrixTravelModel,
    config: CAPAConfig,
) -> float:
    """Compute the Eq.1 FPSA bid for a courier within a cooperating platform."""
    detour_ratio = find_best_auction_detour_ratio(parcel, courier, travel_model)
    p_tau_prime = config.local_sharing_rate_mu1 * parcel.fare
    return platform.base_price + (
        (courier.alpha * detour_ratio) + (courier.beta * courier.service_score)
    ) * platform.sharing_rate_gamma * p_tau_prime


def compute_platform_quality_factor(
    platform: CooperatingPlatform,
    candidate_platforms: Sequence[CooperatingPlatform],
) -> float:
    """Compute the Eq.3 cooperation quality factor f(P)."""
    if len(candidate_platforms) <= 1:
        return 1.0
    max_quality = max(item.historical_quality for item in candidate_platforms)
    if max_quality <= 0:
        return 0.0
    return platform.historical_quality / max_quality


def compute_platform_payment_limit(parcel: Parcel, config: CAPAConfig) -> float:
    """Compute the local-platform upper payment limit inferred from Example 3."""
    return (config.local_sharing_rate_mu1 + config.cross_platform_sharing_rate_mu2) * parcel.fare


def build_cross_assignment(
    parcel: Parcel,
    courier: Courier,
    platform_id: str,
    courier_payment: float,
    platform_payment: float,
) -> Assignment:
    """Construct the realized cross-platform assignment and Eq.5 revenue terms."""
    return Assignment(
        parcel=parcel,
        courier=courier,
        mode="cross",
        platform_id=platform_id,
        courier_payment=courier_payment,
        platform_payment=platform_payment,
        local_platform_revenue=parcel.fare - platform_payment,
        cooperating_platform_revenue=platform_payment - courier_payment,
        courier_revenue=courier_payment,
        utility_value=None,
    )


def apply_cross_assignment(parcel: Parcel, courier: Courier, travel_model: DistanceMatrixTravelModel) -> None:
    """Update a courier route and carried load after a cross assignment is accepted."""
    _, insertion_index = find_best_local_insertion(parcel, courier, travel_model)
    courier.route_locations.insert(insertion_index, parcel.location)
    courier.current_load += parcel.weight


def run_dapa(
    parcels: Sequence[Parcel],
    platforms: Sequence[CooperatingPlatform],
    travel_model: DistanceMatrixTravelModel,
    config: CAPAConfig,
    now: int,
    service_radius_meters: float | None = None,
) -> DAPAResult:
    """Run Algorithm 3 with explicit FPSA, RVA, and upper-limit filtering."""
    cross_assignments: List[Assignment] = []
    unassigned_parcels: List[Parcel] = []
    observed_platform_bids: List[PlatformBid] = []

    for parcel in parcels:
        platform_winners: List[PlatformBid] = []
        for platform in platforms:
            feasible_bids: List[tuple[Courier, float]] = []
            for courier in platform.couriers:
                if not is_feasible_cross_match(
                    parcel,
                    courier,
                    travel_model,
                    now,
                    service_radius_meters=service_radius_meters,
                ):
                    continue
                courier_bid = compute_fpsa_bid(parcel, courier, platform, travel_model, config)
                feasible_bids.append((courier, courier_bid))
            if not feasible_bids:
                continue
            winner_courier, winner_bid = max(feasible_bids, key=lambda item: item[1])
            platform_winners.append(
                PlatformBid(
                    platform_id=platform.platform_id,
                    courier=winner_courier,
                    courier_bid=winner_bid,
                    platform_bid=winner_bid,
                )
            )

        if not platform_winners:
            unassigned_parcels.append(parcel)
            continue

        candidate_platforms = [
            platform for platform in platforms if any(platform.platform_id == bid.platform_id for bid in platform_winners)
        ]
        platform_bid_values: List[PlatformBid] = []
        for winner in platform_winners:
            platform = next(item for item in candidate_platforms if item.platform_id == winner.platform_id)
            quality_factor = compute_platform_quality_factor(platform, candidate_platforms)
            if len(platform_winners) == 1:
                second_layer_bid = winner.courier_bid + config.cross_platform_sharing_rate_mu2 * parcel.fare
            else:
                second_layer_bid = winner.courier_bid + quality_factor * config.cross_platform_sharing_rate_mu2 * parcel.fare
            platform_bid_values.append(
                PlatformBid(
                    platform_id=winner.platform_id,
                    courier=winner.courier,
                    courier_bid=winner.courier_bid,
                    platform_bid=second_layer_bid,
                )
            )

        payment_limit = compute_platform_payment_limit(parcel, config)
        valid_platform_bids = [bid for bid in platform_bid_values if bid.platform_bid <= payment_limit]
        observed_platform_bids.extend(valid_platform_bids)
        if not valid_platform_bids:
            unassigned_parcels.append(parcel)
            continue

        valid_platform_bids.sort(key=lambda item: item.platform_bid)
        winner = valid_platform_bids[0]
        if len(valid_platform_bids) >= 2:
            platform_payment = valid_platform_bids[1].platform_bid
        else:
            platform_payment = winner.courier_bid + config.cross_platform_sharing_rate_mu2 * parcel.fare
            if platform_payment > payment_limit:
                unassigned_parcels.append(parcel)
                continue

        apply_cross_assignment(parcel, winner.courier, travel_model)
        cross_assignments.append(
            build_cross_assignment(
                parcel=parcel,
                courier=winner.courier,
                platform_id=winner.platform_id,
                courier_payment=winner.courier_bid,
                platform_payment=platform_payment,
            )
        )

    return DAPAResult(
        cross_assignments=cross_assignments,
        unassigned_parcels=unassigned_parcels,
        platform_bids=observed_platform_bids,
    )
