"""Paper-faithful local matching implementation for Algorithm 2."""

from __future__ import annotations

from time import perf_counter
from typing import Callable, Iterable, List, Mapping, Sequence

from .constraints import is_deadline_feasible_by_geo, is_within_service_radius, is_within_service_radius_by_geo
from .models import Assignment, CAMAResult, CAPAConfig, CandidatePair, Courier, Parcel, ThresholdHistory
from .utility import (
    DistanceMatrixTravelModel,
    GeoIndex,
    InsertionCache,
    TimingAccumulator,
    calculate_local_revenue_score,
    calculate_local_revenue_threshold,
    calculate_utility,
    compute_local_courier_payment,
    compute_local_platform_revenue_for_local_completion,
)


def is_courier_available(courier: Courier, now: int) -> bool:
    """Return whether the courier is available at the current batch time."""
    return courier.available_from <= now


def any_insertion_preserves_route_deadlines(
    courier: Courier,
    parcel: Parcel,
    travel_model: DistanceMatrixTravelModel,
    now: int,
) -> bool:
    """Return whether at least one insertion index keeps every stop on time.

    Walks the route that would result from inserting ``parcel.location`` at
    each candidate index ``0..len(route_locations)`` and checks accumulated
    arrival times against ``parcel.deadline`` and ``courier.route_deadlines``
    (when present). Returns True as soon as one index satisfies every
    deadline — that is enough to allow CAMA / DAPA to accept the parcel.

    Args:
        courier: Candidate courier carrying ``route_locations`` and optional
            parallel ``route_deadlines`` (any missing per-stop deadline is
            treated as no deadline).
        parcel: Parcel proposed for insertion.
        travel_model: Shared travel model exposing ``travel_time(a, b)``.
        now: Current matching-round timestamp in seconds.
    """

    route = list(courier.route_locations)
    route_deadlines = list(getattr(courier, "route_deadlines", []))
    parcel_deadline = float(parcel.deadline)
    for index in range(len(route) + 1):
        cursor_location = courier.current_location
        cursor_time = float(now)
        downstream_violation = False
        for prefix_index in range(index):
            cursor_time += float(travel_model.travel_time(cursor_location, route[prefix_index]))
            if prefix_index < len(route_deadlines) and cursor_time > float(route_deadlines[prefix_index]):
                downstream_violation = True
                break
            cursor_location = route[prefix_index]
        if downstream_violation:
            continue
        cursor_time += float(travel_model.travel_time(cursor_location, parcel.location))
        if cursor_time > parcel_deadline:
            continue
        cursor_location = parcel.location
        downstream_violation = False
        for suffix_index in range(index, len(route)):
            cursor_time += float(travel_model.travel_time(cursor_location, route[suffix_index]))
            if suffix_index < len(route_deadlines) and cursor_time > float(route_deadlines[suffix_index]):
                downstream_violation = True
                break
            cursor_location = route[suffix_index]
        if not downstream_violation:
            return True
    return False


def is_feasible_local_match(
    parcel: Parcel,
    courier: Courier,
    travel_model: DistanceMatrixTravelModel,
    now: int,
    service_radius_meters: float | None = None,
    geo_index: GeoIndex | None = None,
    speed_m_per_s: float = 0.0,
) -> bool:
    """Check the deadline and capacity constraints required by Algorithm 2."""
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
    if arrival_time > parcel.deadline:
        return False
    return any_insertion_preserves_route_deadlines(courier, parcel, travel_model, now)


def is_feasible_local_candidate(
    parcel: Parcel,
    courier: Courier,
    now: int,
    service_radius_meters: float | None = None,
    geo_index: GeoIndex | None = None,
    speed_m_per_s: float = 0.0,
) -> bool:
    """Cheap shortlist filter for local matching before exact routing is warmed."""

    if not is_courier_available(courier, now):
        return False
    if courier.current_load + parcel.weight > courier.capacity:
        return False
    if not is_deadline_feasible_by_geo(
        courier.current_location, parcel.location, now, parcel.deadline, speed_m_per_s, geo_index,
    ):
        return False
    return is_within_service_radius_by_geo(
        courier.current_location,
        parcel.location,
        service_radius_meters,
        geo_index=geo_index,
    )


def build_local_candidate_shortlist(
    parcels: Sequence[Parcel],
    couriers: Sequence[Courier],
    now: int,
    service_radius_meters: float | None = None,
    geo_index: GeoIndex | None = None,
    speed_m_per_s: float = 0.0,
) -> dict[str, List[Courier]]:
    """Build the parcel-to-courier shortlist used before exact CAMA evaluation."""

    shortlist: dict[str, List[Courier]] = {}
    for parcel in parcels:
        candidates = [
            courier
            for courier in couriers
            if is_feasible_local_candidate(
                parcel,
                courier,
                now,
                service_radius_meters=service_radius_meters,
                geo_index=geo_index,
                speed_m_per_s=speed_m_per_s,
            )
        ]
        if candidates:
            shortlist[parcel.parcel_id] = candidates
    return shortlist


def apply_local_assignment(parcel: Parcel, courier: Courier, insertion_index: int) -> None:  # noqa: D401
    """Insert one accepted local assignment into the courier route bookkeeping."""

    _insert_parcel_into_courier_route(courier, parcel, insertion_index)


def _insert_parcel_into_courier_route(courier: Courier, parcel: Parcel, insertion_index: int) -> None:
    """Update a courier route and carried load after a local assignment is accepted."""
    courier.route_locations.insert(insertion_index, parcel.location)
    route_deadlines = getattr(courier, "route_deadlines", None)
    if route_deadlines is not None:
        route_deadlines.insert(insertion_index, float(parcel.deadline))
    courier.current_load += parcel.weight


def build_local_assignment(
    pair: CandidatePair,
    config: CAPAConfig,
) -> Assignment:
    """Construct the realized local assignment and Eq.5 local revenue terms."""
    courier_payment = compute_local_courier_payment(
        parcel_fare=pair.parcel.fare,
        local_payment_ratio=config.local_payment_ratio_zeta,
    )
    return Assignment(
        parcel=pair.parcel,
        courier=pair.courier,
        mode="local",
        platform_id=None,
        courier_payment=courier_payment,
        platform_payment=courier_payment,
        local_platform_revenue=compute_local_platform_revenue_for_local_completion(
            parcel_fare=pair.parcel.fare,
            local_payment_ratio=config.local_payment_ratio_zeta,
        ),
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
    service_radius_meters: float | None = None,
    timing: TimingAccumulator | None = None,
    insertion_cache: InsertionCache | None = None,
    geo_index: GeoIndex | None = None,
    speed_m_per_s: float = 0.0,
    candidate_couriers_by_parcel: Mapping[str, Sequence[Courier]] | None = None,
    threshold_history: ThresholdHistory | None = None,
    progress_callback: Callable[[Mapping[str, float | int | str]], None] | None = None,
) -> CAMAResult:
    """Run Algorithm 2 exactly at the candidate-set level defined in the paper."""
    started = perf_counter()
    routing_before = 0.0 if timing is None else timing.routing_time_seconds
    insertion_before = 0.0 if timing is None else timing.insertion_time_seconds
    movement_before = 0.0 if timing is None else timing.movement_time_seconds
    all_feasible_pairs: List[CandidatePair] = []
    candidate_best_pairs: List[CandidatePair] = []
    auction_pool: List[Parcel] = []
    progress_stride = max(1, len(parcels) // 100) if parcels else 1

    for parcel_index, parcel in enumerate(parcels, start=1):
        feasible_for_parcel: List[CandidatePair] = []
        shortlisted_couriers = (
            couriers
            if candidate_couriers_by_parcel is None
            else candidate_couriers_by_parcel.get(parcel.parcel_id, ())
        )
        for courier in shortlisted_couriers:
            if not is_feasible_local_match(
                parcel, courier, travel_model, now,
                service_radius_meters=service_radius_meters,
                geo_index=geo_index,
                speed_m_per_s=speed_m_per_s,
            ):
                continue
            utility = calculate_utility(
                parcel,
                courier,
                travel_model,
                config,
                timing=timing,
                insertion_cache=insertion_cache,
                geo_index=geo_index,
            )
            score = calculate_local_revenue_score(parcel, config)
            feasible_for_parcel.append(
                CandidatePair(
                    parcel=parcel,
                    courier=courier,
                    utility=utility,
                    local_revenue_score=score,
                )
            )
        if feasible_for_parcel:
            all_feasible_pairs.extend(feasible_for_parcel)
            best_pair = max(
                feasible_for_parcel,
                key=lambda item: (
                    item.local_revenue_score,
                    item.utility.value,
                    -item.utility.insertion_index,
                ),
            )
            candidate_best_pairs.append(best_pair)
        else:
            auction_pool.append(parcel)
        if progress_callback is not None and (parcel_index == len(parcels) or parcel_index % progress_stride == 0):
            progress_callback(
                {
                    "phase": "cama_parcel_progress",
                    "detail": f"cama {parcel_index}/{len(parcels)}",
                    "completed_units": parcel_index,
                    "total_units": len(parcels),
                    "unit_label": "parcels",
                }
            )

    if threshold_history is None:
        threshold = calculate_local_revenue_threshold(
            (pair.local_revenue_score for pair in all_feasible_pairs),
            config.threshold_omega,
        )
    else:
        threshold_history.add_values(pair.local_revenue_score for pair in all_feasible_pairs)
        threshold = threshold_history.calculate_threshold(config.threshold_omega)

    local_assignments: List[Assignment] = []
    for pair in candidate_best_pairs:
        if pair.local_revenue_score >= threshold:
            apply_local_assignment(pair.parcel, pair.courier, pair.utility.insertion_index)
            local_assignments.append(build_local_assignment(pair, config))
        else:
            auction_pool.append(pair.parcel)

    result = CAMAResult(
        local_assignments=local_assignments,
        auction_pool=auction_pool,
        all_feasible_pairs=all_feasible_pairs,
        candidate_best_pairs=candidate_best_pairs,
        threshold=threshold,
        matching_pairs=local_assignments,
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
