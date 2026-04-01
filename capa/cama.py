"""Paper-faithful local matching implementation for Algorithm 2."""

from __future__ import annotations

from typing import Iterable, List, Sequence

from .models import Assignment, CAMAResult, CAPAConfig, CandidatePair, Courier, Parcel
from .travel import DistanceMatrixTravelModel
from .utility import calculate_threshold, calculate_utility


def is_courier_available(courier: Courier, now: int) -> bool:
    """Return whether the courier is available at the current batch time."""
    return courier.available_from <= now


def is_feasible_local_match(
    parcel: Parcel,
    courier: Courier,
    travel_model: DistanceMatrixTravelModel,
    now: int,
) -> bool:
    """Check the deadline and capacity constraints required by Algorithm 2."""
    if not is_courier_available(courier, now):
        return False
    if courier.current_load + parcel.weight > courier.capacity:
        return False
    arrival_time = now + travel_model.travel_time(courier.current_location, parcel.location)
    return arrival_time <= parcel.deadline


def apply_local_assignment(parcel: Parcel, courier: Courier, insertion_index: int) -> None:
    """Update a courier route and carried load after a local assignment is accepted."""
    courier.route_locations.insert(insertion_index, parcel.location)
    courier.current_load += parcel.weight


def build_local_assignment(
    pair: CandidatePair,
    config: CAPAConfig,
) -> Assignment:
    """Construct the realized local assignment and Eq.5 local revenue terms."""
    courier_payment = config.local_payment_ratio_zeta * pair.parcel.fare
    return Assignment(
        parcel=pair.parcel,
        courier=pair.courier,
        mode="local",
        platform_id=None,
        courier_payment=courier_payment,
        platform_payment=courier_payment,
        local_platform_revenue=pair.parcel.fare - courier_payment,
        cooperating_platform_revenue=0.0,
        courier_revenue=courier_payment,
        utility_value=pair.utility.value,
    )


def run_cama(
    parcels: Sequence[Parcel],
    couriers: Sequence[Courier],
    travel_model: DistanceMatrixTravelModel,
    config: CAPAConfig,
    now: int,
) -> CAMAResult:
    """Run Algorithm 2 exactly at the candidate-set level defined in the paper."""
    all_feasible_pairs: List[CandidatePair] = []
    candidate_best_pairs: List[CandidatePair] = []
    auction_pool: List[Parcel] = []

    for parcel in parcels:
        feasible_for_parcel: List[CandidatePair] = []
        for courier in couriers:
            if not is_feasible_local_match(parcel, courier, travel_model, now):
                continue
            utility = calculate_utility(parcel, courier, travel_model, config)
            feasible_for_parcel.append(CandidatePair(parcel=parcel, courier=courier, utility=utility))
        if feasible_for_parcel:
            all_feasible_pairs.extend(feasible_for_parcel)
            best_pair = max(feasible_for_parcel, key=lambda item: item.utility.value)
            candidate_best_pairs.append(best_pair)
        else:
            auction_pool.append(parcel)

    threshold = calculate_threshold(
        (pair.utility.value for pair in all_feasible_pairs),
        config.threshold_omega,
    )

    local_assignments: List[Assignment] = []
    for pair in candidate_best_pairs:
        if pair.utility.value >= threshold:
            apply_local_assignment(pair.parcel, pair.courier, pair.utility.insertion_index)
            local_assignments.append(build_local_assignment(pair, config))
        else:
            auction_pool.append(pair.parcel)

    return CAMAResult(
        local_assignments=local_assignments,
        auction_pool=auction_pool,
        all_feasible_pairs=all_feasible_pairs,
        candidate_best_pairs=candidate_best_pairs,
        threshold=threshold,
        matching_pairs=local_assignments,
    )
