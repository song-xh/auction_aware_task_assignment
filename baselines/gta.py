"""BaseGTA and ImpGTA baseline runners adapted to the reusable Chengdu environment."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import random
from statistics import fmean
from time import perf_counter
from typing import Any, Callable, Mapping, MutableSequence, Sequence

from capa.config import (
    DEFAULT_CROSS_PLATFORM_SHARING_RATE_MU2,
    DEFAULT_GTA_UNIT_PRICE_PER_KM,
    DEFAULT_IMPGTA_PREDICTION_SAMPLING_SEED,
    DEFAULT_IMPGTA_PREDICTION_SUCCESS_RATE,
    DEFAULT_IMPGTA_WINDOW_SECONDS,
)
from capa.constraints import is_deadline_feasible_by_geo, is_within_service_radius
from capa.dapa import run_dapa
from capa.models import CAPAConfig
from capa.utility import (
    DEFAULT_LOCAL_PAYMENT_RATIO,
    GeoIndex,
    TimedTravelModel,
    TimingAccumulator,
    compute_local_platform_revenue_for_cross_completion,
    compute_local_platform_revenue_for_local_completion,
)
from env.chengdu import (
    apply_assignment_to_legacy_courier,
    compute_delivered_legacy_task_count,
    drain_legacy_routes,
    flatten_partner_couriers,
    framework_movement_callback,
    legacy_platform_to_capa,
    legacy_task_to_parcel,
    partner_courier_snapshot_id,
    sort_legacy_tasks,
)

DEFAULT_UNIT_PRICE_PER_KM = DEFAULT_GTA_UNIT_PRICE_PER_KM


@dataclass(frozen=True)
class GTABid:
    """Store the minimum dispatching price submitted by one platform for one task."""

    platform_id: str
    courier: Any
    dispatch_cost: float
    insertion_index: int = 0


@dataclass(frozen=True)
class AIMOutcome:
    """Store the winner and payment selected by the AIM auction."""

    platform_id: str
    courier: Any
    dispatch_cost: float
    payment: float
    insertion_index: int = 0


def is_idle_legacy_courier(courier: Any) -> bool:
    """Return whether the legacy courier is idle and available for GTA baselines."""
    return not getattr(courier, "re_schedule", [])


def legacy_courier_ready_state(courier: Any, now: int) -> tuple[float, Any]:
    """Return the earliest ready time and service location for one legacy courier."""
    schedule = list(getattr(courier, "re_schedule", []))
    if not schedule:
        return float(now), getattr(courier, "location")
    last_task = schedule[-1]
    ready_time = max(float(now), float(getattr(last_task, "reach_time")))
    return ready_time, getattr(last_task, "l_node")


def compute_dispatch_cost(
    task: Any,
    courier: Any,
    travel_model: Any,
    unit_price_per_km: float = DEFAULT_UNIT_PRICE_PER_KM,
) -> float:
    """Compute the worker dispatch price using the [17] unit-price-per-kilometer setting."""
    distance_meters = float(travel_model.distance(getattr(courier, "location"), getattr(task, "l_node")))
    return (distance_meters / 1000.0) * unit_price_per_km


def compute_dispatch_cost_from_location(
    task: Any,
    start_location: Any,
    travel_model: Any,
    unit_price_per_km: float = DEFAULT_UNIT_PRICE_PER_KM,
) -> float:
    """Compute a dispatch cost from an explicit origin location."""
    distance_meters = float(travel_model.distance(start_location, getattr(task, "l_node")))
    return (distance_meters / 1000.0) * unit_price_per_km


@dataclass(frozen=True)
class LegacyInsertionOption:
    """Store one feasible CPUL insertion option for a GTA courier."""

    insertion_index: int
    incremental_distance_meters: float
    arrival_time: float


def find_best_legacy_insertion_option(
    task: Any,
    courier: Any,
    travel_model: Any,
    now: int,
    service_radius_meters: float | None = None,
    geo_index: GeoIndex | None = None,
    speed_m_per_s: float = 0.0,
) -> LegacyInsertionOption | None:
    """Return the cheapest feasible insertion position for one legacy courier.

    Args:
        task: Legacy parcel/task to evaluate.
        courier: Legacy courier carrying the current route.
        travel_model: Distance/time model bound to the Chengdu graph.
        now: Current simulation time in seconds.
        service_radius_meters: Optional service radius limit.
        geo_index: Optional geographic index for lower-bound pruning.
        speed_m_per_s: Optional travel speed used by geo deadline screening.

    Returns:
        The best feasible insertion option, or `None` when the task cannot be
        inserted under the current capacity/deadline/radius constraints.
    """

    if float(getattr(courier, "re_weight", 0.0)) + float(getattr(task, "weight")) > float(getattr(courier, "max_weight")):
        return None
    schedule = list(getattr(courier, "re_schedule", []))
    pickup_location = getattr(task, "l_node")
    deadline = float(getattr(task, "d_time"))

    def build_candidate(
        insertion_index: int,
        start_location: Any,
        start_time: float,
        next_location: Any | None,
    ) -> LegacyInsertionOption | None:
        if not is_deadline_feasible_by_geo(
            start_location,
            pickup_location,
            int(start_time),
            deadline,
            speed_m_per_s,
            geo_index,
        ):
            return None
        if not is_within_service_radius(
            start_location,
            pickup_location,
            travel_model,
            service_radius_meters,
            geo_index=geo_index,
        ):
            return None
        arrival_time = start_time + float(travel_model.travel_time(start_location, pickup_location))
        if arrival_time > deadline:
            return None
        incremental_distance = float(travel_model.distance(start_location, pickup_location))
        if next_location is not None:
            incremental_distance += float(travel_model.distance(pickup_location, next_location))
            incremental_distance -= float(travel_model.distance(start_location, next_location))
        return LegacyInsertionOption(
            insertion_index=insertion_index,
            incremental_distance_meters=incremental_distance,
            arrival_time=arrival_time,
        )

    candidates: list[LegacyInsertionOption] = []
    if not schedule:
        option = build_candidate(0, getattr(courier, "location"), float(now), None)
        return option

    first_option = build_candidate(
        0,
        getattr(courier, "location"),
        float(now),
        getattr(schedule[0], "l_node"),
    )
    if first_option is not None:
        candidates.append(first_option)

    for index in range(1, len(schedule)):
        previous_task = schedule[index - 1]
        next_task = schedule[index]
        option = build_candidate(
            index,
            getattr(previous_task, "l_node"),
            max(float(now), float(getattr(previous_task, "reach_time"))),
            getattr(next_task, "l_node"),
        )
        if option is not None:
            candidates.append(option)

    append_option = build_candidate(
        len(schedule),
        getattr(schedule[-1], "l_node"),
        max(float(now), float(getattr(schedule[-1], "reach_time"))),
        None,
    )
    if append_option is not None:
        candidates.append(append_option)

    if not candidates:
        return None
    return min(candidates, key=lambda item: (item.incremental_distance_meters, item.insertion_index))


def is_idle_courier_feasible(
    task: Any,
    courier: Any,
    travel_model: Any,
    now: int,
    service_radius_meters: float | None = None,
    geo_index: GeoIndex | None = None,
    speed_m_per_s: float = 0.0,
) -> bool:
    """Check whether an idle legacy courier can still reach the task before its deadline."""
    if not is_idle_legacy_courier(courier):
        return False
    return (
        find_best_legacy_insertion_option(
            task=task,
            courier=courier,
            travel_model=travel_model,
            now=now,
            service_radius_meters=service_radius_meters,
            geo_index=geo_index,
            speed_m_per_s=speed_m_per_s,
        )
        is not None
    )


def is_available_courier_feasible(
    task: Any,
    courier: Any,
    travel_model: Any,
    now: int,
    service_radius_meters: float | None = None,
    geo_index: GeoIndex | None = None,
    speed_m_per_s: float = 0.0,
) -> bool:
    """Check whether a legacy courier can serve the task after finishing its current route."""
    return (
        find_best_legacy_insertion_option(
            task=task,
            courier=courier,
            travel_model=travel_model,
            now=now,
            service_radius_meters=service_radius_meters,
            geo_index=geo_index,
            speed_m_per_s=speed_m_per_s,
        )
        is not None
    )


def select_idle_courier_for_task(
    task: Any,
    couriers: Sequence[Any],
    travel_model: Any,
    now: int,
    unit_price_per_km: float = DEFAULT_UNIT_PRICE_PER_KM,
    service_radius_meters: float | None = None,
    geo_index: GeoIndex | None = None,
    speed_m_per_s: float = 0.0,
) -> GTABid | None:
    """Select the idle feasible courier with the minimum dispatch cost for one task."""
    feasible_bids: list[GTABid] = []
    for courier in couriers:
        option = find_best_legacy_insertion_option(
            task=task,
            courier=courier,
            travel_model=travel_model,
            now=now,
            service_radius_meters=service_radius_meters,
            geo_index=geo_index,
            speed_m_per_s=speed_m_per_s,
        )
        if option is None or not is_idle_legacy_courier(courier):
            continue
        feasible_bids.append(
            GTABid(
                platform_id="",
                courier=courier,
                dispatch_cost=(option.incremental_distance_meters / 1000.0) * unit_price_per_km,
                insertion_index=option.insertion_index,
            )
        )
    if not feasible_bids:
        return None
    return min(feasible_bids, key=lambda item: (item.dispatch_cost, getattr(item.courier, "num", 0)))


def select_available_courier_for_task(
    task: Any,
    couriers: Sequence[Any],
    travel_model: Any,
    now: int,
    unit_price_per_km: float = DEFAULT_UNIT_PRICE_PER_KM,
    service_radius_meters: float | None = None,
    geo_index: GeoIndex | None = None,
    speed_m_per_s: float = 0.0,
) -> GTABid | None:
    """Select the cheapest feasible courier under the Chengdu route-backed availability model."""
    feasible_bids: list[GTABid] = []
    for courier in couriers:
        option = find_best_legacy_insertion_option(
            task=task,
            courier=courier,
            travel_model=travel_model,
            now=now,
            service_radius_meters=service_radius_meters,
            geo_index=geo_index,
            speed_m_per_s=speed_m_per_s,
        )
        if option is None:
            continue
        feasible_bids.append(
            GTABid(
                platform_id="",
                courier=courier,
                dispatch_cost=(option.incremental_distance_meters / 1000.0) * unit_price_per_km,
                insertion_index=option.insertion_index,
            )
        )
    if not feasible_bids:
        return None
    return min(feasible_bids, key=lambda item: (item.dispatch_cost, getattr(item.courier, "num", 0)))


def count_idle_couriers(couriers: Sequence[Any]) -> int:
    """Count the number of idle workers available on one platform."""
    return sum(1 for courier in couriers if is_idle_legacy_courier(courier))


def count_available_couriers(couriers: Sequence[Any], now: int, window_seconds: int = 0) -> int:
    """Count couriers that are idle now or become idle within the requested time window."""
    window_end = float(now + max(0, window_seconds))
    count = 0
    for courier in couriers:
        ready_time, _ = legacy_courier_ready_state(courier, now)
        if ready_time <= window_end:
            count += 1
    return count


def expected_future_reward(future_tasks: Sequence[Any]) -> float:
    """Compute the expected future task reward used by ImpGTA's threshold conditions."""
    if not future_tasks:
        return 0.0
    return float(fmean(float(getattr(task, "fare")) for task in future_tasks))


def should_dispatch_inner_task_impgta(task: Any, idle_worker_count: int, future_tasks: Sequence[Any]) -> bool:
    """Evaluate ImpGTA's inner conditions for the local platform."""
    if idle_worker_count > len(future_tasks):
        return True
    return float(getattr(task, "fare")) >= expected_future_reward(future_tasks)


def should_bid_outer_platform_impgta(dispatch_cost: float, idle_worker_count: int, future_tasks: Sequence[Any]) -> bool:
    """Evaluate ImpGTA's outer conditions for one cooperating platform."""
    if idle_worker_count > len(future_tasks):
        return True
    return dispatch_cost >= expected_future_reward(future_tasks)


def settle_aim_auction(
    task: Any,
    bids: Sequence[GTABid],
    cross_platform_sharing_rate_mu2: float = DEFAULT_CROSS_PLATFORM_SHARING_RATE_MU2,
) -> AIMOutcome | None:
    """Select the AIM winner and convert the critical courier price into platform payment."""
    if not bids:
        return None
    ordered_bids = sorted(bids, key=lambda item: (item.dispatch_cost, item.platform_id))
    winner = ordered_bids[0]
    critical_payment = ordered_bids[1].dispatch_cost if len(ordered_bids) > 1 else winner.dispatch_cost
    payment = min(
        float(getattr(task, "fare")),
        critical_payment + (float(cross_platform_sharing_rate_mu2) * float(getattr(task, "fare"))),
    )
    if payment < winner.dispatch_cost:
        return None
    return AIMOutcome(
        platform_id=winner.platform_id,
        courier=winner.courier,
        dispatch_cost=winner.dispatch_cost,
        payment=payment,
        insertion_index=winner.insertion_index,
    )


def settle_dlam_auction_for_impgta(
    task: Any,
    platform_ids: Sequence[str],
    partner_couriers_by_platform: Mapping[str, Sequence[Any]],
    travel_model: Any,
    now: int,
    platform_base_prices: Mapping[str, float],
    platform_sharing_rates: Mapping[str, float],
    platform_qualities: Mapping[str, float],
    cross_platform_sharing_rate_mu2: float = DEFAULT_CROSS_PLATFORM_SHARING_RATE_MU2,
    service_radius_meters: float | None = None,
    timing: TimingAccumulator | None = None,
    geo_index: GeoIndex | None = None,
    speed_m_per_s: float = 0.0,
) -> AIMOutcome | None:
    """Settle an ImpGTA cross assignment through CAPA's DLAM/DAPA auction.

    Args:
        task: Legacy parcel selected for cross-platform dispatch.
        platform_ids: Partner platforms that passed ImpGTA's prediction rule.
        partner_couriers_by_platform: Active partner courier pools.
        travel_model: Shared travel model used for exact feasibility and bids.
        now: Current simulation time in seconds.
        platform_base_prices: DAPA base price per platform.
        platform_sharing_rates: DAPA first-layer sharing rate per platform.
        platform_qualities: Historical quality proxy per platform.
        cross_platform_sharing_rate_mu2: CAPA second-layer sharing rate.
        service_radius_meters: Optional service-radius constraint.
        timing: Optional accumulator for unified BPT accounting.
        geo_index: Optional geographic lower-bound index.
        speed_m_per_s: Optional travel speed for deadline prefilters.

    Returns:
        Realized auction outcome, or `None` if DLAM finds no valid winner.
    """

    if not platform_ids:
        return None
    parcel = legacy_task_to_parcel(task)
    config = CAPAConfig(cross_platform_sharing_rate_mu2=cross_platform_sharing_rate_mu2)
    platforms = [
        legacy_platform_to_capa(
            platform_id=platform_id,
            couriers=partner_couriers_by_platform[platform_id],
            base_price=platform_base_prices[platform_id],
            sharing_rate_gamma=platform_sharing_rates[platform_id],
            historical_quality=platform_qualities[platform_id],
        )
        for platform_id in platform_ids
    ]
    dapa_result = run_dapa(
        [parcel],
        platforms,
        travel_model,
        config,
        now=now,
        service_radius_meters=service_radius_meters,
        timing=timing,
        geo_index=geo_index,
        speed_m_per_s=speed_m_per_s,
    )
    if not dapa_result.cross_assignments:
        return None
    assignment = dapa_result.cross_assignments[0]
    if assignment.platform_id is None:
        raise ValueError("DAPA returned a cross assignment without a platform id.")
    legacy_courier_lookup = {
        partner_courier_snapshot_id(platform_id, courier): courier
        for platform_id, couriers in partner_couriers_by_platform.items()
        for courier in couriers
    }
    legacy_courier = legacy_courier_lookup[assignment.courier.courier_id]
    insertion_option = find_best_legacy_insertion_option(
        task=task,
        courier=legacy_courier,
        travel_model=travel_model,
        now=now,
        service_radius_meters=service_radius_meters,
        geo_index=geo_index,
        speed_m_per_s=speed_m_per_s,
    )
    if insertion_option is None:
        raise RuntimeError("DAPA selected a courier that is no longer feasible in the legacy route state.")
    return AIMOutcome(
        platform_id=assignment.platform_id,
        courier=legacy_courier,
        dispatch_cost=assignment.courier_payment,
        payment=assignment.platform_payment,
        insertion_index=insertion_option.insertion_index,
    )


def future_tasks_within_window(
    tasks: Sequence[Any],
    now: int,
    window_seconds: int,
    prediction_success_rate: float = DEFAULT_IMPGTA_PREDICTION_SUCCESS_RATE,
    prediction_sampling_seed: int = DEFAULT_IMPGTA_PREDICTION_SAMPLING_SEED,
) -> list[Any]:
    """Collect a deterministically down-sampled future task window for ImpGTA prediction."""
    window_end = now + window_seconds
    future_tasks = [
        task
        for task in tasks
        if now < int(float(getattr(task, "s_time"))) <= window_end
    ]
    if prediction_success_rate <= 0.0:
        return []
    if prediction_success_rate >= 1.0:
        return future_tasks
    rng = random.Random((int(prediction_sampling_seed) * 1_000_003) + int(now))
    return [task for task in future_tasks if rng.random() < float(prediction_success_rate)]


def platform_prediction_sampling_seed(base_seed: int, platform_id: str) -> int:
    """Derive a stable per-platform prediction seed for ImpGTA future windows.

    Args:
        base_seed: Experiment-level prediction sampling seed.
        platform_id: Stable cooperating platform identifier.

    Returns:
        Deterministic integer seed independent of Python hash randomization.
    """

    platform_offset = sum((index + 1) * ord(character) for index, character in enumerate(str(platform_id)))
    return int(base_seed) * 1_000_003 + platform_offset


def advance_simulation(
    local_couriers: MutableSequence[Any],
    partner_couriers_by_platform: Mapping[str, MutableSequence[Any]],
    station_set: Sequence[Any],
    movement_callback: Callable[[MutableSequence[Any], MutableSequence[Any], int, Sequence[Any]], None],
    seconds: int,
) -> None:
    """Advance the legacy simulator by a positive number of seconds."""
    if seconds <= 0:
        return
    movement_callback(local_couriers, flatten_partner_couriers(partner_couriers_by_platform), seconds, station_set)


def _run_gta_environment(
    environment: Any,
    algorithm: str,
    prediction_window_seconds: int | None = None,
    prediction_success_rate: float = DEFAULT_IMPGTA_PREDICTION_SUCCESS_RATE,
    prediction_sampling_seed: int = DEFAULT_IMPGTA_PREDICTION_SAMPLING_SEED,
    unit_price_per_km: float = DEFAULT_UNIT_PRICE_PER_KM,
    local_payment_ratio: float = DEFAULT_LOCAL_PAYMENT_RATIO,
    cross_platform_sharing_rate_mu2: float = DEFAULT_CROSS_PLATFORM_SHARING_RATE_MU2,
    progress_callback: Callable[[Mapping[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Run one GTA-style baseline over the shared Chengdu environment."""
    tasks = sort_legacy_tasks(list(environment.tasks))
    total_task_count = len(tasks)
    if total_task_count == 0:
        return {
            "TR": 0.0,
            "CR": 0.0,
            "BPT": 0.0,
            "delivered_parcels": 0,
            "accepted_assignments": 0,
            "local_assignment_count": 0,
            "cross_assignment_count": 0,
            "unresolved_parcel_count": 0,
            "partner_cross_assignment_counts": {},
            "partner_cross_revenues": {},
        }

    local_couriers = list(environment.local_couriers)
    partner_couriers_by_platform = {
        platform_id: list(couriers)
        for platform_id, couriers in environment.partner_couriers_by_platform.items()
    }
    partner_tasks_by_platform = {
        platform_id: sort_legacy_tasks(list(tasks))
        for platform_id, tasks in getattr(environment, "partner_tasks_by_platform", {}).items()
    }
    platform_base_prices = dict(getattr(environment, "platform_base_prices", {}))
    platform_sharing_rates = dict(getattr(environment, "platform_sharing_rates", {}))
    platform_qualities = dict(getattr(environment, "platform_qualities", {}))
    if algorithm == "impgta":
        missing_partner_task_streams = sorted(set(partner_couriers_by_platform) - set(partner_tasks_by_platform))
        if missing_partner_task_streams:
            raise ValueError(
                "ImpGTA requires partner own-task streams for every cooperating platform: "
                f"missing {missing_partner_task_streams}."
            )
        missing_platform_config = sorted(
            platform_id
            for platform_id in partner_couriers_by_platform
            if (
                platform_id not in platform_base_prices
                or platform_id not in platform_sharing_rates
                or platform_id not in platform_qualities
            )
        )
        if missing_platform_config:
            raise ValueError(
                "ImpGTA requires CAPA/DLAM platform price, sharing-rate, and quality config for every platform: "
                f"missing {missing_platform_config}."
            )
    movement = environment.movement_callback or framework_movement_callback
    timing = TimingAccumulator()
    timed_travel_model = TimedTravelModel(environment.travel_model, timing)
    service_radius_meters = None if getattr(environment, "service_radius_km", None) is None else float(environment.service_radius_km) * 1000.0
    geo_index = getattr(environment, "geo_index", None)
    speed_m_per_s = float(getattr(environment, "travel_speed_m_per_s", 0.0))
    current_time = int(float(getattr(tasks[0], "s_time")))
    task_index = 0
    processed_tasks = 0
    progress_stride = max(1, total_task_count // 100)
    total_profit = 0.0
    accepted_assignments = 0
    accepted_task_ids: set[str] = set()
    processing_time_seconds = 0.0
    local_assignment_count = 0
    cross_assignment_count = 0
    partner_cross_assignment_counts: dict[str, int] = defaultdict(int)
    partner_cross_revenues: dict[str, float] = defaultdict(float)

    while task_index < total_task_count:
        next_arrival_time = int(float(getattr(tasks[task_index], "s_time")))
        advance_simulation(
            local_couriers,
            partner_couriers_by_platform,
            environment.station_set,
            movement,
            next_arrival_time - current_time,
        )
        current_time = next_arrival_time
        arrivals: list[Any] = []
        while task_index < total_task_count and int(float(getattr(tasks[task_index], "s_time"))) == current_time:
            arrivals.append(tasks[task_index])
            task_index += 1

        remaining_tasks = tasks[task_index:]
        if algorithm == "impgta" and prediction_window_seconds is not None:
            local_future_tasks = future_tasks_within_window(
                remaining_tasks,
                current_time,
                prediction_window_seconds,
                prediction_success_rate=prediction_success_rate,
                prediction_sampling_seed=prediction_sampling_seed,
            )
        else:
            local_future_tasks = []

        for task in arrivals:
            started = perf_counter()
            routing_before = timing.routing_time_seconds
            insertion_before = timing.insertion_time_seconds
            local_bid = select_available_courier_for_task(
                task=task,
                couriers=local_couriers,
                travel_model=timed_travel_model,
                now=current_time,
                unit_price_per_km=unit_price_per_km,
                service_radius_meters=service_radius_meters,
                geo_index=geo_index,
                speed_m_per_s=speed_m_per_s,
            )
            if local_bid is not None:
                if algorithm == "basegta" or should_dispatch_inner_task_impgta(
                    task=task,
                    idle_worker_count=count_available_couriers(
                        local_couriers,
                        current_time,
                        prediction_window_seconds or 0,
                    ),
                    future_tasks=local_future_tasks,
                ):
                    apply_assignment_to_legacy_courier(task, local_bid.courier, local_bid.insertion_index)
                    accepted_assignments += 1
                    local_assignment_count += 1
                    accepted_task_ids.add(str(getattr(task, "num")))
                    total_profit += compute_local_platform_revenue_for_local_completion(
                        parcel_fare=float(getattr(task, "fare")),
                        local_payment_ratio=local_payment_ratio,
                    )
                    processing_time_seconds += max(
                        0.0,
                        perf_counter() - started - (timing.routing_time_seconds - routing_before) - (timing.insertion_time_seconds - insertion_before),
                    )
                    processed_tasks += 1
                    if progress_callback is not None and (processed_tasks == total_task_count or processed_tasks % progress_stride == 0):
                        progress_callback(
                            {
                                "phase": "dispatch",
                                "detail": f"task {processed_tasks}/{total_task_count} at t={current_time}",
                                "completed_units": processed_tasks,
                                "total_units": total_task_count,
                                "unit_label": "tasks",
                            }
                        )
                    continue

            outer_bids: list[GTABid] = []
            dlam_platform_ids: list[str] = []
            for platform_id, partner_couriers in partner_couriers_by_platform.items():
                partner_future_tasks: list[Any] = []
                if algorithm == "impgta" and prediction_window_seconds is not None:
                    partner_future_tasks = future_tasks_within_window(
                        partner_tasks_by_platform[platform_id],
                        current_time,
                        prediction_window_seconds,
                        prediction_success_rate=prediction_success_rate,
                        prediction_sampling_seed=platform_prediction_sampling_seed(
                            prediction_sampling_seed,
                            platform_id,
                        ),
                    )
                partner_bid = select_available_courier_for_task(
                    task=task,
                    couriers=partner_couriers,
                    travel_model=timed_travel_model,
                    now=current_time,
                    unit_price_per_km=unit_price_per_km,
                    service_radius_meters=service_radius_meters,
                    geo_index=geo_index,
                    speed_m_per_s=speed_m_per_s,
                )
                if partner_bid is None:
                    continue
                if algorithm == "impgta":
                    if not should_bid_outer_platform_impgta(
                        dispatch_cost=partner_bid.dispatch_cost,
                        idle_worker_count=count_available_couriers(
                            partner_couriers,
                            current_time,
                            prediction_window_seconds or 0,
                        ),
                        future_tasks=partner_future_tasks,
                    ):
                        continue
                    dlam_platform_ids.append(platform_id)
                    continue
                outer_bids.append(
                    GTABid(
                        platform_id=platform_id,
                        courier=partner_bid.courier,
                        dispatch_cost=partner_bid.dispatch_cost,
                        insertion_index=partner_bid.insertion_index,
                    )
                )

            if algorithm == "impgta":
                outcome = settle_dlam_auction_for_impgta(
                    task=task,
                    platform_ids=dlam_platform_ids,
                    partner_couriers_by_platform=partner_couriers_by_platform,
                    travel_model=timed_travel_model,
                    now=current_time,
                    platform_base_prices=platform_base_prices,
                    platform_sharing_rates=platform_sharing_rates,
                    platform_qualities=platform_qualities,
                    cross_platform_sharing_rate_mu2=cross_platform_sharing_rate_mu2,
                    service_radius_meters=service_radius_meters,
                    timing=timing,
                    geo_index=geo_index,
                    speed_m_per_s=speed_m_per_s,
                )
            else:
                outcome = settle_aim_auction(
                    task,
                    outer_bids,
                    cross_platform_sharing_rate_mu2=cross_platform_sharing_rate_mu2,
                )
            if outcome is not None:
                apply_assignment_to_legacy_courier(task, outcome.courier, outcome.insertion_index)
                accepted_assignments += 1
                cross_assignment_count += 1
                accepted_task_ids.add(str(getattr(task, "num")))
                total_profit += compute_local_platform_revenue_for_cross_completion(
                    parcel_fare=float(getattr(task, "fare")),
                    platform_payment=outcome.payment,
                )
                partner_cross_assignment_counts[outcome.platform_id] += 1
                partner_cross_revenues[outcome.platform_id] += float(outcome.payment)
            processing_time_seconds += max(
                0.0,
                perf_counter() - started - (timing.routing_time_seconds - routing_before) - (timing.insertion_time_seconds - insertion_before),
            )
            processed_tasks += 1
            if progress_callback is not None and (processed_tasks == total_task_count or processed_tasks % progress_stride == 0):
                progress_callback(
                    {
                        "phase": "dispatch",
                        "detail": f"task {processed_tasks}/{total_task_count} at t={current_time}",
                        "completed_units": processed_tasks,
                        "total_units": total_task_count,
                        "unit_label": "tasks",
                    }
                )

    if accepted_assignments > 0:
        drain_legacy_routes(
            local_couriers=local_couriers,
            partner_couriers_by_platform=partner_couriers_by_platform,
            station_set=environment.station_set,
            step_seconds=60,
            movement_callback=movement,
        )
    delivered_parcels = compute_delivered_legacy_task_count(
        accepted_task_ids,
        local_couriers,
        partner_couriers_by_platform,
    )

    return {
        "TR": total_profit,
        "CR": delivered_parcels / total_task_count,
        "BPT": processing_time_seconds,
        "delivered_parcels": delivered_parcels,
        "accepted_assignments": accepted_assignments,
        "local_assignment_count": local_assignment_count,
        "cross_assignment_count": cross_assignment_count,
        "unresolved_parcel_count": max(0, total_task_count - local_assignment_count - cross_assignment_count),
        "partner_cross_assignment_counts": dict(partner_cross_assignment_counts),
        "partner_cross_revenues": dict(partner_cross_revenues),
    }


def run_basegta_baseline_environment(
    environment: Any,
    unit_price_per_km: float = DEFAULT_UNIT_PRICE_PER_KM,
    local_payment_ratio: float = DEFAULT_LOCAL_PAYMENT_RATIO,
    cross_platform_sharing_rate_mu2: float = DEFAULT_CROSS_PLATFORM_SHARING_RATE_MU2,
    progress_callback: Callable[[Mapping[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Run BaseGTA on the shared Chengdu environment."""
    return _run_gta_environment(
        environment=environment,
        algorithm="basegta",
        prediction_window_seconds=None,
        unit_price_per_km=unit_price_per_km,
        local_payment_ratio=local_payment_ratio,
        cross_platform_sharing_rate_mu2=cross_platform_sharing_rate_mu2,
        progress_callback=progress_callback,
    )


def run_impgta_baseline_environment(
    environment: Any,
    prediction_window_seconds: int = DEFAULT_IMPGTA_WINDOW_SECONDS,
    prediction_success_rate: float = DEFAULT_IMPGTA_PREDICTION_SUCCESS_RATE,
    prediction_sampling_seed: int = DEFAULT_IMPGTA_PREDICTION_SAMPLING_SEED,
    unit_price_per_km: float = DEFAULT_UNIT_PRICE_PER_KM,
    local_payment_ratio: float = DEFAULT_LOCAL_PAYMENT_RATIO,
    cross_platform_sharing_rate_mu2: float = DEFAULT_CROSS_PLATFORM_SHARING_RATE_MU2,
    progress_callback: Callable[[Mapping[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Run ImpGTA on the shared Chengdu environment with a fixed future window."""
    return _run_gta_environment(
        environment=environment,
        algorithm="impgta",
        prediction_window_seconds=prediction_window_seconds,
        prediction_success_rate=prediction_success_rate,
        prediction_sampling_seed=prediction_sampling_seed,
        unit_price_per_km=unit_price_per_km,
        local_payment_ratio=local_payment_ratio,
        cross_platform_sharing_rate_mu2=cross_platform_sharing_rate_mu2,
        progress_callback=progress_callback,
    )
