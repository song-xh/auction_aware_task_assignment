"""Paper-faithful dual-layer auction implementation for Algorithm 3."""

from __future__ import annotations

from time import perf_counter
from typing import Callable, List, Mapping, Sequence

from .cache import InsertionCache
from .cama import is_courier_available
from .constraints import is_deadline_feasible_by_geo, is_within_service_radius
from .geo import GeoIndex
from .models import (
    Assignment,
    CAPAConfig,
    CooperatingPlatform,
    Courier,
    DAPAResult,
    Parcel,
    PlatformBid,
)
from .timing import TimingAccumulator
from .utility import (
    DistanceMatrixTravelModel,
    compute_cooperating_platform_revenue,
    compute_local_platform_revenue_for_cross_completion,
    find_best_auction_detour_ratio,
    find_best_local_insertion,
)


def is_feasible_cross_match(
    parcel: Parcel,
    courier: Courier,
    travel_model: DistanceMatrixTravelModel,
    now: int,
    service_radius_meters: float | None = None,
    geo_index: GeoIndex | None = None,
    speed_m_per_s: float = 0.0,
) -> bool:
    """Check the validity condition required before a courier may enter FPSA."""
    if not is_courier_available(courier, now):
        return False
    if courier.current_load + parcel.weight > courier.capacity:
        return False
    if not is_deadline_feasible_by_geo(
        courier.current_location, parcel.location, now, parcel.deadline, speed_m_per_s, geo_index,
    ):
        return False
    if not is_within_service_radius(
        courier.current_location, parcel.location, travel_model, service_radius_meters, geo_index=geo_index,
    ):
        return False
    arrival_time = now + travel_model.travel_time(courier.current_location, parcel.location)
    return arrival_time <= parcel.deadline


def compute_fpsa_bid(
    parcel: Parcel,
    courier: Courier,
    platform: CooperatingPlatform,
    travel_model: DistanceMatrixTravelModel,
    config: CAPAConfig,
    timing: TimingAccumulator | None = None,
    insertion_cache: InsertionCache | None = None,
) -> float:
    """Compute the Eq.1 FPSA bid for a courier within a cooperating platform."""
    detour_ratio = find_best_auction_detour_ratio(
        parcel,
        courier,
        travel_model,
        timing=timing,
        insertion_cache=insertion_cache,
    )
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
        local_platform_revenue=compute_local_platform_revenue_for_cross_completion(parcel.fare, platform_payment),
        cooperating_platform_revenue=compute_cooperating_platform_revenue(platform_payment, courier_payment),
        courier_revenue=courier_payment,
        utility_value=None,
    )


def apply_cross_assignment(
    parcel: Parcel,
    courier: Courier,
    travel_model: DistanceMatrixTravelModel,
    timing: TimingAccumulator | None = None,
    insertion_cache: InsertionCache | None = None,
) -> None:
    """Update a courier route and carried load after a cross assignment is accepted."""
    _, insertion_index = find_best_local_insertion(
        parcel,
        courier,
        travel_model,
        timing=timing,
        insertion_cache=insertion_cache,
    )
    courier.route_locations.insert(insertion_index, parcel.location)
    courier.current_load += parcel.weight


def run_dapa(
    parcels: Sequence[Parcel],
    platforms: Sequence[CooperatingPlatform],
    travel_model: DistanceMatrixTravelModel,
    config: CAPAConfig,
    now: int,
    service_radius_meters: float | None = None,
    timing: TimingAccumulator | None = None,
    insertion_cache: InsertionCache | None = None,
    geo_index: GeoIndex | None = None,
    speed_m_per_s: float = 0.0,
    progress_callback: Callable[[Mapping[str, float | int | str]], None] | None = None,
) -> DAPAResult:
    """Run Algorithm 3 with explicit FPSA, RVA, and upper-limit filtering."""
    started = perf_counter()
    routing_before = 0.0 if timing is None else timing.routing_time_seconds
    insertion_before = 0.0 if timing is None else timing.insertion_time_seconds
    movement_before = 0.0 if timing is None else timing.movement_time_seconds
    cross_assignments: List[Assignment] = []
    unassigned_parcels: List[Parcel] = []
    observed_platform_bids: List[PlatformBid] = []
    progress_stride = max(1, len(parcels) // 100) if parcels else 1

    for parcel_index, parcel in enumerate(parcels, start=1):
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
                    geo_index=geo_index,
                    speed_m_per_s=speed_m_per_s,
                ):
                    continue
                courier_bid = compute_fpsa_bid(
                    parcel,
                    courier,
                    platform,
                    travel_model,
                    config,
                    timing=timing,
                    insertion_cache=insertion_cache,
                )
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
        else:
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
            else:
                valid_platform_bids.sort(key=lambda item: item.platform_bid)
                winner = valid_platform_bids[0]
                if len(valid_platform_bids) >= 2:
                    platform_payment = valid_platform_bids[1].platform_bid
                else:
                    platform_payment = winner.courier_bid + config.cross_platform_sharing_rate_mu2 * parcel.fare
                    if platform_payment > payment_limit:
                        unassigned_parcels.append(parcel)
                        platform_payment = None
                if platform_payment is not None:
                    apply_cross_assignment(parcel, winner.courier, travel_model, timing=timing, insertion_cache=insertion_cache)
                    cross_assignments.append(
                        build_cross_assignment(
                            parcel=parcel,
                            courier=winner.courier,
                            platform_id=winner.platform_id,
                            courier_payment=winner.courier_bid,
                            platform_payment=platform_payment,
                        )
                    )
        if progress_callback is not None and (parcel_index == len(parcels) or parcel_index % progress_stride == 0):
            progress_callback(
                {
                    "phase": "dapa_parcel_progress",
                    "detail": f"dapa {parcel_index}/{len(parcels)}",
                    "completed_units": parcel_index,
                    "total_units": len(parcels),
                    "unit_label": "parcels",
                }
            )

    result = DAPAResult(
        cross_assignments=cross_assignments,
        unassigned_parcels=unassigned_parcels,
        platform_bids=observed_platform_bids,
    )
    if timing is not None:
        elapsed = perf_counter() - started
        timing.decision_time_seconds += max(
            0.0,
            elapsed
            - (timing.routing_time_seconds - routing_before)
            - (timing.insertion_time_seconds - insertion_before)
            - (timing.movement_time_seconds - movement_before),
        )
    return result
