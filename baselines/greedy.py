"""Unified Greedy baseline with paper-faithful revenue accounting."""

from __future__ import annotations

import io
import re
from contextlib import redirect_stdout
from time import perf_counter
from typing import Any, Callable, Mapping, Sequence

from capa.cache import InsertionCache
from capa.cama import is_feasible_local_match
from capa.geo import GeoIndex
from capa.timing import TimedTravelModel, TimingAccumulator
from capa.utility import (
    DEFAULT_LOCAL_PAYMENT_RATIO,
    compute_local_platform_revenue_for_local_completion,
    find_best_local_insertion,
)
from env.chengdu import (
    LegacyCourierSnapshotCache,
    apply_assignment_to_legacy_courier,
    drain_legacy_routes,
    framework_movement_callback,
    legacy_task_to_parcel,
    sort_legacy_tasks,
)

from .common import project_courier_to_capa


GREEDY_RESULT_PATTERN = re.compile(
    r"完成任务个数:\s*(?P<completed>[0-9.]+)\s*,\s*总失败个数:\s*(?P<failed>[0-9.]+)\s*,\s*任务完成率:\s*(?P<cr>[0-9.]+)\s*%.*?"
    r"批处理耗时:\s*(?P<bpt>[0-9.]+)\s*ms,\s*任务均报价:\s*(?P<avg_bid>[0-9.]+)\s*,\s*平台总报价:\s*(?P<platform_bid>[0-9.]+)\s*,\s*平台总收益:\s*(?P<tr>[0-9.]+)",
    re.DOTALL,
)


def safe_average(total: float, count: float) -> float:
    """Return a zero-safe average for legacy Greedy aggregate statistics."""
    if count == 0:
        return 0.0
    return total / count


def parse_greedy_metrics(output: str) -> dict[str, float]:
    """Parse the legacy Greedy stdout summary into normalized metric keys."""
    match = GREEDY_RESULT_PATTERN.search(output)
    if match is None:
        raise ValueError("Failed to parse Greedy output summary.")
    completed = int(float(match.group("completed")))
    return {
        "TR": float(match.group("tr")),
        "CR": float(match.group("cr")) / 100.0,
        "BPT": float(match.group("bpt")) / 1000.0,
        "delivered_parcels": completed,
        "accepted_assignments": completed,
    }


def run_legacy_greedy_stdout(
    environment: Any,
    batch_size: int,
    utility: float = 0.5,
    realtime: int = 1,
) -> dict[str, float]:
    """Run the original legacy Greedy entrypoint and parse its printed aggregates.

    Args:
        environment: Prepared unified Chengdu environment.
        batch_size: Batch duration in seconds.
        utility: Legacy greedy bid utility parameter.
        realtime: Legacy simulator step size.

    Returns:
        Normalized metric dictionary parsed from stdout.
    """

    import Framework_ChengDu as framework

    stdout_buffer = io.StringIO()
    with redirect_stdout(stdout_buffer):
        framework.Greedy(
            list(environment.station_set),
            list(environment.local_couriers),
            list(environment.tasks),
            batch_size,
            utility,
            realtime,
            getattr(environment, "service_radius_km", None),
        )
    return parse_greedy_metrics(stdout_buffer.getvalue())


def run_greedy_baseline_environment(
    environment: Any,
    batch_size: int,
    utility: float = 0.5,
    realtime: int = 1,
    local_payment_ratio: float = DEFAULT_LOCAL_PAYMENT_RATIO,
    progress_callback: Callable[[Mapping[str, Any]], None] | None = None,
) -> dict[str, float]:
    """Run a local-only greedy baseline with CAPA-aligned Eq.5 revenue accounting.

    Args:
        environment: Shared Chengdu environment.
        batch_size: Accepted for interface compatibility with the unified runner.
        utility: Legacy greedy bid utility parameter.
        realtime: Time step in seconds between greedy decisions.
        local_payment_ratio: Fixed inner-courier payment ratio `zeta`.

        progress_callback: Optional structured progress sink for live experiment UIs.

    Returns:
        Normalized `TR`/`CR`/`BPT` metrics.
    """

    del batch_size
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

    local_couriers = list(environment.local_couriers)
    movement = environment.movement_callback or framework_movement_callback
    timing = TimingAccumulator()
    timed_travel_model = TimedTravelModel(environment.travel_model, timing)
    snapshot_cache = LegacyCourierSnapshotCache()
    insertion_cache = InsertionCache()
    geo_index = getattr(environment, "geo_index", None)
    speed_m_per_s = float(getattr(environment, "travel_speed_m_per_s", 0.0))
    service_radius_meters = (
        None if getattr(environment, "service_radius_km", None) is None else float(environment.service_radius_km) * 1000.0
    )
    current_time = int(float(getattr(tasks[0], "s_time")))
    task_index = 0
    processed_tasks = 0
    progress_stride = max(1, total_tasks // 100)
    accepted_assignments = 0
    total_revenue = 0.0
    processing_time_seconds = 0.0

    while task_index < total_tasks:
        next_arrival_time = int(float(getattr(tasks[task_index], "s_time")))
        advance_seconds = max(0, next_arrival_time - current_time)
        if advance_seconds > 0:
            movement_started = perf_counter()
            movement(local_couriers, [], advance_seconds, environment.station_set)
            timing.movement_time_seconds += perf_counter() - movement_started
        current_time = next_arrival_time
        arrivals: list[Any] = []
        while task_index < total_task_count(tasks) and int(float(getattr(tasks[task_index], "s_time"))) == current_time:
            arrivals.append(tasks[task_index])
            task_index += 1

        for task in arrivals:
            started = perf_counter()
            routing_before = timing.routing_time_seconds
            insertion_before = timing.insertion_time_seconds
            selection = select_greedy_assignment(
                task=task,
                couriers=local_couriers,
                travel_model=timed_travel_model,
                now=current_time,
                utility=utility,
                service_radius_meters=service_radius_meters,
                timing=timing,
                snapshot_cache=snapshot_cache,
                insertion_cache=insertion_cache,
                geo_index=geo_index,
                speed_m_per_s=speed_m_per_s,
            )
            if selection is not None:
                courier, insertion_index, _ = selection
                apply_assignment_to_legacy_courier(task, courier, insertion_index)
                accepted_assignments += 1
                total_revenue += compute_local_platform_revenue_for_local_completion(
                    parcel_fare=float(getattr(task, "fare")),
                    local_payment_ratio=local_payment_ratio,
                )
            processing_time_seconds += max(
                0.0,
                perf_counter() - started - (timing.routing_time_seconds - routing_before) - (timing.insertion_time_seconds - insertion_before),
            )
            processed_tasks += 1
            if progress_callback is not None and (processed_tasks == total_tasks or processed_tasks % progress_stride == 0):
                progress_callback(
                    {
                        "phase": "dispatch",
                        "detail": f"task {processed_tasks}/{total_tasks} at t={current_time}",
                        "completed_units": processed_tasks,
                        "total_units": total_tasks,
                        "unit_label": "tasks",
                    }
                )

    if accepted_assignments > 0:
        drain_legacy_routes(
            local_couriers=local_couriers,
            partner_couriers_by_platform={},
            station_set=environment.station_set,
            step_seconds=max(1, realtime),
            movement_callback=movement,
        )

    return {
        "TR": total_revenue,
        "CR": accepted_assignments / total_tasks,
        "BPT": processing_time_seconds,
        "delivered_parcels": accepted_assignments,
        "accepted_assignments": accepted_assignments,
    }


def select_greedy_assignment(
    task: Any,
    couriers: Sequence[Any],
    travel_model: Any,
    now: int,
    utility: float,
    service_radius_meters: float | None,
    timing: TimingAccumulator | None = None,
    snapshot_cache: LegacyCourierSnapshotCache | None = None,
    insertion_cache: InsertionCache | None = None,
    geo_index: GeoIndex | None = None,
    speed_m_per_s: float = 0.0,
) -> tuple[Any, int, float] | None:
    """Choose the minimum-bid local courier for one task under legacy Greedy bidding.

    Args:
        task: Legacy Chengdu task object.
        couriers: Candidate local couriers.
        travel_model: Shared travel model.
        now: Current simulation time.
        utility: Legacy greedy bid scaling factor.
        service_radius_meters: Maximum courier-to-task distance.
        timing: Optional timing accumulator.

    Returns:
        `(courier, insertion_index, bid)` for the selected local courier, or `None`.
    """

    parcel = legacy_task_to_parcel(task)
    best_choice: tuple[Any, int, float] | None = None
    for courier in couriers:
        snapshot = project_courier_to_capa(
            courier,
            courier_id=f"greedy-{getattr(courier, 'num')}",
            snapshot_cache=snapshot_cache,
        )
        if not is_feasible_local_match(
            parcel=parcel,
            courier=snapshot,
            travel_model=travel_model,
            now=now,
            service_radius_meters=service_radius_meters,
            geo_index=geo_index,
            speed_m_per_s=speed_m_per_s,
        ):
            continue
        bid, insertion_index = compute_greedy_bid(
            parcel=parcel,
            courier_snapshot=snapshot,
            legacy_courier=courier,
            travel_model=travel_model,
            utility=utility,
            timing=timing,
            insertion_cache=insertion_cache,
        )
        candidate = (courier, insertion_index, bid)
        if best_choice is None or (bid, getattr(courier, "num", 0)) < (best_choice[2], getattr(best_choice[0], "num", 0)):
            best_choice = candidate
    return best_choice


def compute_greedy_bid(
    parcel: Any,
    courier_snapshot: Any,
    legacy_courier: Any,
    travel_model: Any,
    utility: float,
    timing: TimingAccumulator | None = None,
    insertion_cache: InsertionCache | None = None,
) -> tuple[float, int]:
    """Compute the legacy Greedy local bid and insertion index for one courier-task pair.

    Args:
        parcel: CAPA parcel snapshot converted from the legacy task.
        courier_snapshot: CAPA courier snapshot.
        legacy_courier: Original legacy courier object carrying weight preferences.
        travel_model: Shared travel model.
        utility: Legacy bid scaling factor `u`.
        timing: Optional timing accumulator.

    Returns:
        `(bid, insertion_index)` for the minimum-bid insertion position.
    """

    remaining_capacity = max(float(getattr(legacy_courier, "max_weight")) - float(getattr(legacy_courier, "re_weight", 0.0)), 1e-9)
    weight_term = float(parcel.weight) / remaining_capacity
    preference_w = float(getattr(legacy_courier, "w", 0.5))
    preference_c = float(getattr(legacy_courier, "c", 0.5))
    local_ratio, insertion_index = find_best_local_insertion(
        parcel,
        courier_snapshot,
        travel_model,
        timing=timing,
        insertion_cache=insertion_cache,
    )
    detour_rate = 0.0 if local_ratio >= 1.0 else 1.0 / max(local_ratio, 1e-9)
    bid = 2.0 + (preference_w * weight_term + preference_c * detour_rate) * float(utility) * float(parcel.fare)
    bid = min(bid, 2.0 + float(utility) * float(parcel.fare))
    return bid, insertion_index


def total_task_count(tasks: Sequence[Any]) -> int:
    """Return the total number of tasks in a sorted task sequence.

    Args:
        tasks: Ordered legacy task sequence.

    Returns:
        Number of tasks.
    """

    return len(tasks)
