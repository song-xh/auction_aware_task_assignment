"""Chengdu-adapted RamCOM baseline implementation."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import math
import random
from time import perf_counter
from typing import Any, Callable, Mapping, Sequence

from capa.config import DEFAULT_CAPA_BATCH_SIZE, DEFAULT_RAMCOM_RANDOM_SEED
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
    compute_delivered_legacy_task_ids,
    drain_legacy_routes,
    flatten_partner_couriers,
    framework_movement_callback,
    get_model_release_time,
    get_true_deadline,
    group_legacy_tasks_by_batch,
    sort_legacy_tasks,
)

from .common import build_legacy_feasible_insertions, extract_worker_history_values, mean_decision_time, sum_delivered_assignment_revenue


@dataclass(frozen=True)
class RamCOMPaymentEstimate:
    """Store one RamCOM maximum-expected-revenue payment estimate.

    Args:
        payment: Selected outer-worker payment.
        expected_revenue: RamCOM expected revenue `(fare - payment) * Pr_accept`.
        set_accept_prob: Probability that at least one feasible outer worker accepts.
    """

    payment: float
    expected_revenue: float
    set_accept_prob: float


def estimate_reservation_payment(
    request: Any,
    insertion: Any,
    local_payment_ratio: float = DEFAULT_LOCAL_PAYMENT_RATIO,
) -> float:
    """Estimate an outer courier reservation payment from CPUL insertion state.

    Args:
        request: Request-like object exposing `fare`.
        insertion: Feasible insertion carrying `distance_meters`.
        local_payment_ratio: Fixed courier-payment ratio used elsewhere in CPUL.

    Returns:
        A positive payment threshold no larger than the request fare.
    """

    fare = float(getattr(request, "fare"))
    distance_component = max(0.0, float(getattr(insertion, "distance_meters", 0.0))) / 1000.0
    reservation = float(local_payment_ratio) * fare + distance_component
    return min(fare, max(1e-9, reservation))


def worker_acceptance_probability(
    payment: float,
    history_values: Sequence[float],
    reservation_payment: float | None = None,
) -> float:
    """Estimate one worker's cooperative acceptance probability from completed-value history.

    Args:
        payment: Offered cooperative payment.
        history_values: Historical completed request values for one worker.
        reservation_payment: Explicit CPUL reservation estimate used when no
            empirical history is available.

    Returns:
        The empirical acceptance probability in `[0, 1]`.
    """

    if not history_values:
        if reservation_payment is None:
            return 0.0
        if reservation_payment <= 0:
            return 1.0
        return min(1.0, max(0.0, float(payment) / float(reservation_payment)))
    accepted = sum(1 for value in history_values if float(value) <= payment)
    return accepted / len(history_values)


def cooperative_acceptance_probability(
    payment: float,
    outer_worker_histories: Sequence[Sequence[float]],
    reservation_payments: Sequence[float | None] | None = None,
) -> float:
    """Aggregate outer-worker acceptance probabilities under an independence assumption.

    Args:
        payment: Offered cooperative payment.
        outer_worker_histories: Historical completed values for each candidate outer worker.
        reservation_payments: Reservation estimates aligned with candidate histories.

    Returns:
        Probability that at least one outer worker accepts the cooperative task.
    """

    reservations = list(reservation_payments or [])
    if len(reservations) < len(outer_worker_histories):
        reservations.extend([None] * (len(outer_worker_histories) - len(reservations)))
    elif len(reservations) > len(outer_worker_histories):
        reservations = reservations[: len(outer_worker_histories)]
    rejection_product = 1.0
    for history, reservation in zip(outer_worker_histories, reservations):
        rejection_product *= 1.0 - worker_acceptance_probability(payment, history, reservation)
    return 1.0 - rejection_product


def estimate_ramcom_outer_payment(
    request: Any,
    outer_worker_histories: Sequence[Sequence[float]],
    reservation_payments: Sequence[float | None] | None = None,
) -> RamCOMPaymentEstimate:
    """Estimate the outer payment maximizing RamCOM expected revenue.

    Args:
        request: Request-like object exposing `fare`.
        outer_worker_histories: Historical completed values for each candidate outer worker.
        reservation_payments: Reservation estimates aligned with candidate histories.

    Returns:
        Selected payment, expected revenue, and aggregate acceptance probability.
    """

    fare = float(getattr(request, "fare"))
    candidate_levels = {fare}
    for history in outer_worker_histories:
        for value in history:
            if 0.0 < float(value) <= fare:
                candidate_levels.add(float(value))
    for reservation in reservation_payments or []:
        if reservation is not None and 0.0 < float(reservation) <= fare:
            candidate_levels.add(float(reservation))
    best_payment = fare
    best_revenue = float("-inf")
    best_accept_prob = 0.0
    for payment in sorted(candidate_levels):
        accept_prob = cooperative_acceptance_probability(payment, outer_worker_histories, reservation_payments)
        expected_revenue = (fare - payment) * accept_prob
        is_better = expected_revenue > best_revenue + 1e-12
        is_tie = abs(expected_revenue - best_revenue) <= 1e-12
        if is_better or (is_tie and (payment < best_payment or (payment == best_payment and accept_prob > best_accept_prob))):
            best_revenue = expected_revenue
            best_payment = payment
            best_accept_prob = accept_prob
    return RamCOMPaymentEstimate(
        payment=best_payment,
        expected_revenue=max(0.0, best_revenue),
        set_accept_prob=best_accept_prob,
    )


def choose_outer_payment_by_expected_revenue(
    request: Any,
    outer_worker_histories: Sequence[Sequence[float]],
    reservation_payments: Sequence[float | None] | None = None,
) -> float:
    """Choose the cooperative payment maximizing expected revenue for RamCOM.

    Args:
        request: Request-like object exposing `fare`.
        outer_worker_histories: Historical completed values for each candidate outer worker.
        reservation_payments: Reservation estimates aligned with candidate histories.

    Returns:
        The payment that maximizes `(fare - payment) * acceptance_probability`.
    """

    return estimate_ramcom_outer_payment(
        request=request,
        outer_worker_histories=outer_worker_histories,
        reservation_payments=reservation_payments,
    ).payment


def run_ramcom_baseline_environment(
    environment: Any,
    random_seed: int = DEFAULT_RAMCOM_RANDOM_SEED,
    batch_size: int = DEFAULT_CAPA_BATCH_SIZE,
    local_payment_ratio: float = DEFAULT_LOCAL_PAYMENT_RATIO,
    progress_callback: Callable[[Mapping[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Run the Chengdu-adapted RamCOM baseline on the unified environment.

    Args:
        environment: Shared Chengdu environment.
        random_seed: Random seed controlling threshold and acceptance sampling.
        batch_size: Batch duration used to expose the shared CPUL batch input surface.

    Returns:
        Normalized `TR`/`CR`/`BPT` metrics.
    """

    tasks = sort_legacy_tasks(list(environment.tasks))
    total_tasks = len(tasks)
    if total_tasks == 0:
        return {
            "method": "RamCOM-CPUL",
            "seed": random_seed,
            "theta": None,
            "k": None,
            "threshold": None,
            "max_fare": None,
            "acceptance_model": "empirical_history_or_reservation_based",
            "payment_search": "history_or_reservation_candidates",
            "batch_size": batch_size,
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
            "decision_trace": [],
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
    max_fare = max(float(getattr(task, "fare")) for task in tasks)
    theta = max(1, math.ceil(math.log(max_fare + 1.0)))
    k = rng.randint(1, theta)
    threshold = math.exp(k)
    current_time = int(get_model_release_time(tasks[0]))
    accepted_assignments = 0
    accepted_task_ids: set[str] = set()
    accepted_revenues_by_task_id: dict[str, float] = {}
    processing_time_seconds = 0.0
    local_assignment_count = 0
    cross_assignment_count = 0
    partner_cross_assignment_counts: dict[str, int] = defaultdict(int)
    partner_cross_revenues: dict[str, float] = defaultdict(float)
    progress_stride = max(1, total_tasks // 100)
    decision_trace: list[dict[str, Any]] = []
    batches = group_legacy_tasks_by_batch(tasks, batch_size)
    processed_tasks = 0

    for batch_index, batch_tasks in enumerate(batches, start=1):
        for task in sort_legacy_tasks(batch_tasks):
            processed_tasks += 1
            task_index = processed_tasks
            trace_entry: dict[str, Any] = {
                "parcel_id": str(getattr(task, "num")),
                "fare": float(getattr(task, "fare")),
                "arrival_time": float(get_model_release_time(task)),
                "deadline": float(get_true_deadline(task)),
                "threshold": threshold,
                "batch_index": batch_index,
                "num_feasible_inner": 0,
                "num_feasible_outer": 0,
                "payment_e": None,
                "expected_revenue": None,
                "set_accept_prob": None,
                "selected_courier": None,
                "selected_platform": None,
                "reject_reason": None,
            }

            arrival_time = int(get_model_release_time(task))
            if arrival_time > current_time:
                movement_started = perf_counter()
                movement(local_couriers, flatten_partner_couriers(partner_couriers_by_platform), arrival_time - current_time, environment.station_set)
                timing.movement_time_seconds += perf_counter() - movement_started
                current_time = arrival_time
            if get_true_deadline(task) < current_time:
                trace_entry["branch"] = "expired"
                trace_entry["reject_reason"] = "deadline_expired"
                decision_trace.append(trace_entry)
                if progress_callback is not None and (task_index == total_tasks or task_index % progress_stride == 0):
                    progress_callback(
                        {
                            "phase": "dispatch",
                            "detail": f"task {task_index}/{total_tasks} expired at t={current_time}",
                            "completed_units": task_index,
                            "total_units": total_tasks,
                            "unit_label": "tasks",
                        }
                    )
                continue

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
                trace_entry["num_feasible_inner"] = len(inner_candidates)
                if inner_candidates:
                    chosen = rng.choice(inner_candidates)
                    apply_assignment_to_legacy_courier(task, chosen.courier, chosen.insertion_index)
                    courier_cache_id = f"ramcom-inner-{getattr(chosen.courier, 'num')}"
                    snapshot_cache.invalidate(courier_cache_id)
                    insertion_cache.invalidate_courier(courier_cache_id)
                    task_id = str(getattr(task, "num"))
                    accepted_revenues_by_task_id[task_id] = compute_local_platform_revenue_for_local_completion(
                        parcel_fare=float(getattr(task, "fare")),
                        local_payment_ratio=local_payment_ratio,
                    )
                    accepted_assignments += 1
                    local_assignment_count += 1
                    accepted_task_ids.add(task_id)
                    trace_entry["branch"] = "high_value_local"
                    trace_entry["selected_courier"] = str(getattr(chosen.courier, "num", ""))
                    assigned = True

            if not assigned:
                outer_candidates: list[tuple[str, Any]] = []
                outer_histories: list[list[float]] = []
                outer_reservations: list[float] = []
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
                        outer_reservations.append(
                            estimate_reservation_payment(
                                task,
                                insertion,
                                local_payment_ratio=local_payment_ratio,
                            )
                        )

                trace_entry["num_feasible_outer"] = len(outer_candidates)
                if outer_candidates:
                    payment_estimate = estimate_ramcom_outer_payment(
                        task,
                        outer_histories,
                        outer_reservations,
                    )
                    outer_payment = payment_estimate.payment
                    trace_entry["payment_e"] = outer_payment
                    trace_entry["expected_revenue"] = payment_estimate.expected_revenue
                    trace_entry["set_accept_prob"] = payment_estimate.set_accept_prob
                    if outer_payment <= 0.0 or outer_payment > float(getattr(task, "fare")):
                        trace_entry["branch"] = "outer_invalid_payment"
                        trace_entry["reject_reason"] = "invalid_payment"
                    else:
                        accepted_outer: list[tuple[str, Any]] = []
                        outer_samples: list[dict[str, Any]] = []
                        for (platform_id, insertion), history, reservation in zip(outer_candidates, outer_histories, outer_reservations):
                            acceptance_probability = worker_acceptance_probability(outer_payment, history, reservation)
                            accepted = rng.random() <= acceptance_probability
                            outer_samples.append(
                                {
                                    "platform": platform_id,
                                    "courier": str(getattr(insertion.courier, "num", "")),
                                    "acceptance_probability": acceptance_probability,
                                    "accepted": accepted,
                                }
                            )
                            if accepted:
                                accepted_outer.append((platform_id, insertion))
                        trace_entry["outer_samples"] = outer_samples
                        if accepted_outer:
                            selected_platform, selected_insertion = min(
                                accepted_outer,
                                key=lambda item: (item[1].distance_meters, item[0], getattr(item[1].courier, "num", 0)),
                            )
                            apply_assignment_to_legacy_courier(task, selected_insertion.courier, selected_insertion.insertion_index)
                            courier_cache_id = f"ramcom-{selected_platform}-{getattr(selected_insertion.courier, 'num')}"
                            snapshot_cache.invalidate(courier_cache_id)
                            insertion_cache.invalidate_courier(courier_cache_id)
                            task_id = str(getattr(task, "num"))
                            accepted_revenues_by_task_id[task_id] = compute_local_platform_revenue_for_cross_completion(
                                parcel_fare=float(getattr(task, "fare")),
                                platform_payment=outer_payment,
                            )
                            accepted_assignments += 1
                            cross_assignment_count += 1
                            accepted_task_ids.add(task_id)
                            partner_cross_assignment_counts[selected_platform] += 1
                            partner_cross_revenues[selected_platform] += float(outer_payment)
                            trace_entry["branch"] = "outer_success"
                            trace_entry["selected_platform"] = selected_platform
                            trace_entry["selected_courier"] = str(getattr(selected_insertion.courier, "num", ""))
                        else:
                            trace_entry["branch"] = "outer_rejected_by_all"
                            trace_entry["reject_reason"] = "rejected_by_all"
                else:
                    trace_entry["branch"] = "outer_no_candidate"
                    trace_entry["reject_reason"] = "no_feasible_outer"
            decision_trace.append(trace_entry)

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
    delivered_task_ids = compute_delivered_legacy_task_ids(
        accepted_task_ids,
        local_couriers,
        partner_couriers_by_platform,
    )
    delivered_parcels = len(delivered_task_ids)
    total_revenue = sum_delivered_assignment_revenue(accepted_revenues_by_task_id, delivered_task_ids)

    return {
        "method": "RamCOM-CPUL",
        "seed": random_seed,
        "theta": theta,
        "k": k,
        "threshold": threshold,
        "max_fare": max_fare,
        "acceptance_model": "empirical_history_or_reservation_based",
        "payment_search": "history_or_reservation_candidates",
        "batch_size": batch_size,
        "TR": total_revenue,
        "CR": delivered_parcels / total_tasks,
        "BPT": mean_decision_time(processing_time_seconds, total_tasks),
        "delivered_parcels": delivered_parcels,
        "accepted_assignments": accepted_assignments,
        "local_assignment_count": local_assignment_count,
        "cross_assignment_count": cross_assignment_count,
        "unresolved_parcel_count": max(0, total_tasks - local_assignment_count - cross_assignment_count),
        "partner_cross_assignment_counts": dict(partner_cross_assignment_counts),
        "partner_cross_revenues": dict(partner_cross_revenues),
        "decision_trace": decision_trace,
    }
