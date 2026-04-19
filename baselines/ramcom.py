"""Chengdu-adapted RamCOM baseline implementation."""

from __future__ import annotations

import math
import random
from time import perf_counter
from typing import Any, Callable, Mapping, Sequence

from capa.config import DEFAULT_RAMCOM_RANDOM_SEED
from capa.utility import (
    DEFAULT_LOCAL_PAYMENT_RATIO,
    InsertionCache,
    TimedTravelModel,
    TimingAccumulator,
    compute_local_platform_revenue_for_cross_completion,
    compute_local_platform_revenue_for_local_completion,
)
from env.chengdu import (
    LegacyCourierSnapshotCache,
    apply_assignment_to_legacy_courier,
    drain_legacy_routes,
    flatten_partner_couriers,
    framework_movement_callback,
    sort_legacy_tasks,
)

from .common import build_legacy_feasible_insertions, extract_worker_history_values


def worker_acceptance_probability(payment: float, history_values: Sequence[float]) -> float:
    """Estimate one worker's cooperative acceptance probability from completed-value history.

    Args:
        payment: Offered cooperative payment.
        history_values: Historical completed request values for one worker.

    Returns:
        The empirical acceptance probability in `[0, 1]`.
    """

    if not history_values:
        return 0.0
    accepted = sum(1 for value in history_values if float(value) <= payment)
    return accepted / len(history_values)


def cooperative_acceptance_probability(payment: float, outer_worker_histories: Sequence[Sequence[float]]) -> float:
    """Aggregate outer-worker acceptance probabilities under an independence assumption.

    Args:
        payment: Offered cooperative payment.
        outer_worker_histories: Historical completed values for each candidate outer worker.

    Returns:
        Probability that at least one outer worker accepts the cooperative task.
    """

    rejection_product = 1.0
    for history in outer_worker_histories:
        rejection_product *= 1.0 - worker_acceptance_probability(payment, history)
    return 1.0 - rejection_product


def choose_outer_payment_by_expected_revenue(request: Any, outer_worker_histories: Sequence[Sequence[float]]) -> float:
    """Choose the cooperative payment maximizing expected revenue for RamCOM.

    Args:
        request: Request-like object exposing `fare`.
        outer_worker_histories: Historical completed values for each candidate outer worker.

    Returns:
        The payment that maximizes `(fare - payment) * acceptance_probability`.
    """

    fare = float(getattr(request, "fare"))
    candidate_levels = {fare}
    for history in outer_worker_histories:
        for value in history:
            if 0.0 < float(value) <= fare:
                candidate_levels.add(float(value))
    best_payment = fare
    best_revenue = float("-inf")
    for payment in sorted(candidate_levels):
        expected_revenue = (fare - payment) * cooperative_acceptance_probability(payment, outer_worker_histories)
        if expected_revenue > best_revenue:
            best_revenue = expected_revenue
            best_payment = payment
    return best_payment


def run_ramcom_baseline_environment(
    environment: Any,
    random_seed: int = DEFAULT_RAMCOM_RANDOM_SEED,
    local_payment_ratio: float = DEFAULT_LOCAL_PAYMENT_RATIO,
    progress_callback: Callable[[Mapping[str, Any]], None] | None = None,
) -> dict[str, float]:
    """Run the Chengdu-adapted RamCOM baseline on the unified environment.

    Args:
        environment: Shared Chengdu environment.
        random_seed: Random seed controlling threshold and acceptance sampling.

    Returns:
        Normalized `TR`/`CR`/`BPT` metrics.
    """

    tasks = sort_legacy_tasks(list(environment.tasks))
    total_tasks = len(tasks)
    if total_tasks == 0:
        return {
            "TR": 0.0,
            "CR": 0.0,
            "BPT": 0.0,
            "delivered_parcels": 0,
            "accepted_assignments": 0,
        }

    rng = random.Random(random_seed)
    timing = TimingAccumulator()
    timed_travel_model = TimedTravelModel(environment.travel_model, timing)
    snapshot_cache = LegacyCourierSnapshotCache()
    insertion_cache = InsertionCache()
    geo_index = getattr(environment, "geo_index", None)
    speed_m_per_s = float(getattr(environment, "travel_speed_m_per_s", 0.0))
    local_couriers = list(environment.local_couriers)
    partner_couriers_by_platform = {
        platform_id: list(couriers)
        for platform_id, couriers in environment.partner_couriers_by_platform.items()
    }
    movement = environment.movement_callback or framework_movement_callback
    service_radius_meters = None if getattr(environment, "service_radius_km", None) is None else float(environment.service_radius_km) * 1000.0
    theta = max(1, math.ceil(math.log(max(float(getattr(task, "fare")) for task in tasks) + 1.0)))
    threshold = math.exp(rng.randint(1, theta))
    current_time = int(float(getattr(tasks[0], "s_time")))
    accepted_assignments = 0
    total_revenue = 0.0
    processing_time_seconds = 0.0
    progress_stride = max(1, total_tasks // 100)

    for task_index, task in enumerate(tasks, start=1):
        arrival_time = int(float(getattr(task, "s_time")))
        if arrival_time > current_time:
            movement_started = perf_counter()
            movement(local_couriers, flatten_partner_couriers(partner_couriers_by_platform), arrival_time - current_time, environment.station_set)
            timing.movement_time_seconds += perf_counter() - movement_started
            current_time = arrival_time

        started = perf_counter()
        routing_before = timing.routing_time_seconds
        insertion_before = timing.insertion_time_seconds
        assigned = False
        if float(getattr(task, "fare")) > threshold:
            inner_candidates = build_legacy_feasible_insertions(
                task=task,
                couriers=local_couriers,
                travel_model=timed_travel_model,
                now=current_time,
                service_radius_meters=service_radius_meters,
                courier_id_prefix="ramcom-inner",
                timing=timing,
                snapshot_cache=snapshot_cache,
                insertion_cache=insertion_cache,
                geo_index=geo_index,
                speed_m_per_s=speed_m_per_s,
            )
            if inner_candidates:
                chosen = rng.choice(inner_candidates)
                apply_assignment_to_legacy_courier(task, chosen.courier, chosen.insertion_index)
                courier_cache_id = f"ramcom-inner-{getattr(chosen.courier, 'num')}"
                snapshot_cache.invalidate(courier_cache_id)
                insertion_cache.invalidate_courier(courier_cache_id)
                total_revenue += compute_local_platform_revenue_for_local_completion(
                    parcel_fare=float(getattr(task, "fare")),
                    local_payment_ratio=local_payment_ratio,
                )
                accepted_assignments += 1
                assigned = True

        if not assigned:
            outer_candidates: list[tuple[str, Any]] = []
            outer_histories: list[list[float]] = []
            for platform_id, couriers in partner_couriers_by_platform.items():
                feasible = build_legacy_feasible_insertions(
                    task=task,
                    couriers=couriers,
                    travel_model=timed_travel_model,
                    now=current_time,
                    service_radius_meters=service_radius_meters,
                    courier_id_prefix=f"ramcom-{platform_id}",
                    timing=timing,
                    snapshot_cache=snapshot_cache,
                    insertion_cache=insertion_cache,
                    geo_index=geo_index,
                    speed_m_per_s=speed_m_per_s,
                )
                for insertion in feasible:
                    outer_candidates.append((platform_id, insertion))
                    outer_histories.append(extract_worker_history_values(insertion.courier))

            if outer_candidates:
                outer_payment = choose_outer_payment_by_expected_revenue(task, outer_histories)
                accepted_outer: list[tuple[str, Any]] = []
                for (platform_id, insertion), history in zip(outer_candidates, outer_histories):
                    acceptance_probability = worker_acceptance_probability(outer_payment, history)
                    if rng.random() <= acceptance_probability:
                        accepted_outer.append((platform_id, insertion))
                if accepted_outer:
                    selected_platform, selected_insertion = min(
                        accepted_outer,
                        key=lambda item: (item[1].distance_meters, item[0], getattr(item[1].courier, "num", 0)),
                    )
                    apply_assignment_to_legacy_courier(task, selected_insertion.courier, selected_insertion.insertion_index)
                    courier_cache_id = f"ramcom-{selected_platform}-{getattr(selected_insertion.courier, 'num')}"
                    snapshot_cache.invalidate(courier_cache_id)
                    insertion_cache.invalidate_courier(courier_cache_id)
                    total_revenue += compute_local_platform_revenue_for_cross_completion(
                        parcel_fare=float(getattr(task, "fare")),
                        platform_payment=outer_payment,
                    )
                    accepted_assignments += 1

        processing_time_seconds += max(
            0.0,
            perf_counter() - started - (timing.routing_time_seconds - routing_before) - (timing.insertion_time_seconds - insertion_before),
        )
        if progress_callback is not None and (task_index == total_tasks or task_index % progress_stride == 0):
            progress_callback(
                {
                    "phase": "dispatch",
                    "detail": f"task {task_index}/{total_tasks} at t={current_time}",
                    "completed_units": task_index,
                    "total_units": total_tasks,
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
        "TR": total_revenue,
        "CR": accepted_assignments / total_tasks,
        "BPT": processing_time_seconds,
        "delivered_parcels": accepted_assignments,
        "accepted_assignments": accepted_assignments,
    }
