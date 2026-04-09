"""BaseGTA and ImpGTA baseline runners adapted to the reusable Chengdu environment."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import fmean
from time import perf_counter
from typing import Any, Callable, Mapping, MutableSequence, Sequence

from capa.config import DEFAULT_GTA_UNIT_PRICE_PER_KM, DEFAULT_IMPGTA_WINDOW_SECONDS
from capa.constraints import is_deadline_feasible_by_geo, is_within_service_radius
from capa.geo import GeoIndex
from capa.timing import TimedTravelModel, TimingAccumulator
from capa.utility import (
    DEFAULT_LOCAL_PAYMENT_RATIO,
    compute_local_platform_revenue_for_cross_completion,
    compute_local_platform_revenue_for_local_completion,
)
from env.chengdu import (
    apply_assignment_to_legacy_courier,
    drain_legacy_routes,
    flatten_partner_couriers,
    framework_movement_callback,
    sort_legacy_tasks,
)

DEFAULT_UNIT_PRICE_PER_KM = DEFAULT_GTA_UNIT_PRICE_PER_KM


@dataclass(frozen=True)
class GTABid:
    """Store the minimum dispatching price submitted by one platform for one task."""

    platform_id: str
    courier: Any
    dispatch_cost: float


@dataclass(frozen=True)
class AIMOutcome:
    """Store the winner and payment selected by the AIM auction."""

    platform_id: str
    courier: Any
    dispatch_cost: float
    payment: float


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
    if float(getattr(courier, "re_weight", 0.0)) + float(getattr(task, "weight")) > float(getattr(courier, "max_weight")):
        return False
    if not is_deadline_feasible_by_geo(
        getattr(courier, "location"),
        getattr(task, "l_node"),
        now,
        float(getattr(task, "d_time")),
        speed_m_per_s,
        geo_index,
    ):
        return False
    if not is_within_service_radius(
        getattr(courier, "location"),
        getattr(task, "l_node"),
        travel_model,
        service_radius_meters,
        geo_index=geo_index,
    ):
        return False
    arrival_time = now + float(travel_model.travel_time(getattr(courier, "location"), getattr(task, "l_node")))
    return arrival_time <= float(getattr(task, "d_time"))


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
    ready_time, ready_location = legacy_courier_ready_state(courier, now)
    if not is_idle_legacy_courier(courier) and float(getattr(courier, "max_weight")) < float(getattr(task, "weight")):
        return False
    if is_idle_legacy_courier(courier):
        remaining_capacity = float(getattr(courier, "max_weight")) - float(getattr(courier, "re_weight", 0.0))
    else:
        remaining_capacity = float(getattr(courier, "max_weight"))
    if remaining_capacity < float(getattr(task, "weight")):
        return False
    if not is_deadline_feasible_by_geo(
        ready_location,
        getattr(task, "l_node"),
        int(ready_time),
        float(getattr(task, "d_time")),
        speed_m_per_s,
        geo_index,
    ):
        return False
    if not is_within_service_radius(
        ready_location,
        getattr(task, "l_node"),
        travel_model,
        service_radius_meters,
        geo_index=geo_index,
    ):
        return False
    arrival_time = ready_time + float(travel_model.travel_time(ready_location, getattr(task, "l_node")))
    return arrival_time <= float(getattr(task, "d_time"))


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
        if not is_idle_courier_feasible(
            task,
            courier,
            travel_model,
            now,
            service_radius_meters=service_radius_meters,
            geo_index=geo_index,
            speed_m_per_s=speed_m_per_s,
        ):
            continue
        feasible_bids.append(
            GTABid(
                platform_id="",
                courier=courier,
                dispatch_cost=compute_dispatch_cost(task, courier, travel_model, unit_price_per_km),
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
        if not is_available_courier_feasible(
            task=task,
            courier=courier,
            travel_model=travel_model,
            now=now,
            service_radius_meters=service_radius_meters,
            geo_index=geo_index,
            speed_m_per_s=speed_m_per_s,
        ):
            continue
        _, ready_location = legacy_courier_ready_state(courier, now)
        feasible_bids.append(
            GTABid(
                platform_id="",
                courier=courier,
                dispatch_cost=compute_dispatch_cost_from_location(
                    task=task,
                    start_location=ready_location,
                    travel_model=travel_model,
                    unit_price_per_km=unit_price_per_km,
                ),
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


def settle_aim_auction(task: Any, bids: Sequence[GTABid]) -> AIMOutcome | None:
    """Select the AIM winner by minimum bid and pay the second-lowest critical price."""
    if not bids:
        return None
    ordered_bids = sorted(bids, key=lambda item: (item.dispatch_cost, item.platform_id))
    winner = ordered_bids[0]
    critical_payment = ordered_bids[1].dispatch_cost if len(ordered_bids) > 1 else winner.dispatch_cost
    payment = min(float(getattr(task, "fare")), critical_payment)
    if payment < winner.dispatch_cost:
        return None
    return AIMOutcome(
        platform_id=winner.platform_id,
        courier=winner.courier,
        dispatch_cost=winner.dispatch_cost,
        payment=payment,
    )


def future_tasks_within_window(tasks: Sequence[Any], now: int, window_seconds: int) -> list[Any]:
    """Collect tasks whose arrival times fall inside the ImpGTA future observation window."""
    window_end = now + window_seconds
    return [
        task
        for task in tasks
        if now < int(float(getattr(task, "s_time"))) <= window_end
    ]


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
    unit_price_per_km: float = DEFAULT_UNIT_PRICE_PER_KM,
    local_payment_ratio: float = DEFAULT_LOCAL_PAYMENT_RATIO,
    progress_callback: Callable[[Mapping[str, Any]], None] | None = None,
) -> dict[str, float]:
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
        }

    local_couriers = list(environment.local_couriers)
    partner_couriers_by_platform = {
        platform_id: list(couriers)
        for platform_id, couriers in environment.partner_couriers_by_platform.items()
    }
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
    processing_time_seconds = 0.0

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
        local_future_tasks = (
            future_tasks_within_window(remaining_tasks, current_time, prediction_window_seconds)
            if algorithm == "impgta" and prediction_window_seconds is not None
            else []
        )

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
                    apply_assignment_to_legacy_courier(task, local_bid.courier, len(getattr(local_bid.courier, "re_schedule")))
                    accepted_assignments += 1
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
            for platform_id, partner_couriers in partner_couriers_by_platform.items():
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
                        future_tasks=[],
                    ):
                        continue
                outer_bids.append(
                    GTABid(
                        platform_id=platform_id,
                        courier=partner_bid.courier,
                        dispatch_cost=partner_bid.dispatch_cost,
                    )
                )

            outcome = settle_aim_auction(task, outer_bids)
            if outcome is not None:
                apply_assignment_to_legacy_courier(task, outcome.courier, len(getattr(outcome.courier, "re_schedule")))
                accepted_assignments += 1
                total_profit += compute_local_platform_revenue_for_cross_completion(
                    parcel_fare=float(getattr(task, "fare")),
                    platform_payment=outcome.payment,
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

    if accepted_assignments > 0:
        drain_legacy_routes(
            local_couriers=local_couriers,
            partner_couriers_by_platform=partner_couriers_by_platform,
            station_set=environment.station_set,
            step_seconds=60,
            movement_callback=movement,
        )

    return {
        "TR": total_profit,
        "CR": accepted_assignments / total_task_count,
        "BPT": processing_time_seconds,
        "delivered_parcels": accepted_assignments,
        "accepted_assignments": accepted_assignments,
    }


def run_basegta_baseline_environment(
    environment: Any,
    unit_price_per_km: float = DEFAULT_UNIT_PRICE_PER_KM,
    local_payment_ratio: float = DEFAULT_LOCAL_PAYMENT_RATIO,
    progress_callback: Callable[[Mapping[str, Any]], None] | None = None,
) -> dict[str, float]:
    """Run BaseGTA on the shared Chengdu environment."""
    return _run_gta_environment(
        environment=environment,
        algorithm="basegta",
        prediction_window_seconds=None,
        unit_price_per_km=unit_price_per_km,
        local_payment_ratio=local_payment_ratio,
        progress_callback=progress_callback,
    )


def run_impgta_baseline_environment(
    environment: Any,
    prediction_window_seconds: int = DEFAULT_IMPGTA_WINDOW_SECONDS,
    unit_price_per_km: float = DEFAULT_UNIT_PRICE_PER_KM,
    local_payment_ratio: float = DEFAULT_LOCAL_PAYMENT_RATIO,
    progress_callback: Callable[[Mapping[str, Any]], None] | None = None,
) -> dict[str, float]:
    """Run ImpGTA on the shared Chengdu environment with a fixed future window."""
    return _run_gta_environment(
        environment=environment,
        algorithm="impgta",
        prediction_window_seconds=prediction_window_seconds,
        unit_price_per_km=unit_price_per_km,
        local_payment_ratio=local_payment_ratio,
        progress_callback=progress_callback,
    )
