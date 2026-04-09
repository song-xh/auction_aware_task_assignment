"""Chengdu-adapted MRA baseline implementation."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any, Callable, Mapping, Sequence

from capa.cache import InsertionCache
from capa.config import (
    DEFAULT_COURIER_ALPHA,
    DEFAULT_COURIER_BETA,
    DEFAULT_MRA_BASE_PRICE,
    DEFAULT_MRA_SHARING_RATE,
)
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
    group_legacy_tasks_by_batch,
    legacy_task_to_parcel,
)

from .common import build_legacy_feasible_insertions, project_courier_to_capa



@dataclass(frozen=True)
class MRAEdge:
    """Store one feasible courier-parcel edge in the multi-round assignment graph."""

    task: Any
    courier: Any
    bid: float
    insertion_index: int


def compute_mra_bid(
    task: Any,
    courier: Any,
    travel_model: Any,
    feasible_count: int,
    base_price: float = DEFAULT_MRA_BASE_PRICE,
    sharing_rate: float = DEFAULT_MRA_SHARING_RATE,
    timing: TimingAccumulator | None = None,
    insertion_cache: InsertionCache | None = None,
    snapshot_cache: LegacyCourierSnapshotCache | None = None,
    geo_index: GeoIndex | None = None,
) -> float:
    """Compute the Chengdu-adapted MRA bid described in `docs/mra.md`.

    Args:
        task: Legacy task object.
        courier: Legacy courier object.
        travel_model: Shared travel model.
        feasible_count: Number of feasible couriers for the current task.
        base_price: MRA base bid offset.
        sharing_rate: MRA fare scaling factor.

    Returns:
        The bid value for this courier-task pair.
    """

    parcel = legacy_task_to_parcel(task)
    snapshot = project_courier_to_capa(
        courier,
        courier_id=f"mra-{getattr(courier, 'num')}",
        snapshot_cache=snapshot_cache,
    )
    remaining_capacity = max(snapshot.capacity - snapshot.current_load, 1e-9)
    capacity_term = 1.0 - (parcel.weight / remaining_capacity)
    local_ratio, _ = find_best_local_insertion(
        parcel,
        snapshot,
        travel_model,
        timing=timing,
        insertion_cache=insertion_cache,
        geo_index=geo_index,
    )
    detour_term = 1.0 - local_ratio
    if feasible_count <= 1:
        return base_price + sharing_rate * parcel.fare
    alpha = float(getattr(courier, "w", DEFAULT_COURIER_ALPHA))
    beta = float(getattr(courier, "c", DEFAULT_COURIER_BETA))
    return base_price + (alpha * capacity_term + beta * detour_term) * sharing_rate * parcel.fare


def run_mra_baseline_environment(
    environment: Any,
    batch_size: int,
    base_price: float = DEFAULT_MRA_BASE_PRICE,
    sharing_rate: float = DEFAULT_MRA_SHARING_RATE,
    local_payment_ratio: float = DEFAULT_LOCAL_PAYMENT_RATIO,
    progress_callback: Callable[[Mapping[str, Any]], None] | None = None,
) -> dict[str, float]:
    """Run the Chengdu-adapted MRA baseline on the unified environment.

    Args:
        environment: Shared Chengdu environment.
        batch_size: Batch window in seconds.
        base_price: MRA base bid offset.
        sharing_rate: MRA fare scaling factor.

    Returns:
        Normalized `TR`/`CR`/`BPT` metrics.
    """

    tasks = list(environment.tasks)
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
    service_radius_meters = None if getattr(environment, "service_radius_km", None) is None else float(environment.service_radius_km) * 1000.0
    backlog: list[Any] = []
    accepted_assignments = 0
    total_revenue = 0.0
    batches = group_legacy_tasks_by_batch(tasks, batch_size)
    first_batch_start = int(float(getattr(min(tasks, key=lambda item: float(getattr(item, "s_time"))), "s_time")))

    total_batches = len(batches)
    for batch_index, bucket in enumerate(batches, start=1):
        now = first_batch_start + (batch_index - 1) * batch_size
        unresolved = list(backlog) + list(bucket)
        remaining = list(unresolved)
        while remaining:
            round_started = perf_counter()
            routing_before = timing.routing_time_seconds
            insertion_before = timing.insertion_time_seconds
            movement_before = timing.movement_time_seconds
            graph_edges: list[MRAEdge] = []
            for task in remaining:
                feasible = build_legacy_feasible_insertions(
                    task=task,
                    couriers=local_couriers,
                    travel_model=timed_travel_model,
                    now=now,
                    service_radius_meters=service_radius_meters,
                    courier_id_prefix="mra",
                    timing=timing,
                    snapshot_cache=snapshot_cache,
                    insertion_cache=insertion_cache,
                    geo_index=geo_index,
                    speed_m_per_s=speed_m_per_s,
                )
                for insertion in feasible:
                    graph_edges.append(
                        MRAEdge(
                            task=task,
                            courier=insertion.courier,
                            bid=compute_mra_bid(
                                task=task,
                                courier=insertion.courier,
                                travel_model=timed_travel_model,
                                feasible_count=len(feasible),
                                base_price=base_price,
                                sharing_rate=sharing_rate,
                                timing=timing,
                                insertion_cache=insertion_cache,
                                snapshot_cache=snapshot_cache,
                                geo_index=geo_index,
                            ),
                            insertion_index=insertion.insertion_index,
                        )
                    )
            if not graph_edges:
                break

            ordered_edges = sorted(graph_edges, key=lambda edge: (edge.bid, str(getattr(edge.task, "num")), getattr(edge.courier, "num", 0)))
            used_couriers: set[int] = set()
            used_tasks: set[str] = set()
            round_assignments: list[MRAEdge] = []
            for edge in ordered_edges:
                task_id = str(getattr(edge.task, "num"))
                courier_id = int(getattr(edge.courier, "num"))
                if task_id in used_tasks or courier_id in used_couriers:
                    continue
                best_for_task = min(
                    (candidate for candidate in graph_edges if str(getattr(candidate.task, "num")) == task_id),
                    key=lambda candidate: candidate.bid,
                )
                if best_for_task is not edge:
                    continue
                round_assignments.append(edge)
                used_tasks.add(task_id)
                used_couriers.add(courier_id)

            if not round_assignments:
                break

            for edge in round_assignments:
                apply_assignment_to_legacy_courier(edge.task, edge.courier, edge.insertion_index)
                courier_cache_id = f"mra-{getattr(edge.courier, 'num')}"
                snapshot_cache.invalidate(courier_cache_id)
                insertion_cache.invalidate_courier(courier_cache_id)
                total_revenue += compute_local_platform_revenue_for_local_completion(
                    parcel_fare=float(getattr(edge.task, "fare")),
                    local_payment_ratio=local_payment_ratio,
                )
                accepted_assignments += 1

            remaining = [task for task in remaining if str(getattr(task, "num")) not in used_tasks]
            elapsed = perf_counter() - round_started
            timing.decision_time_seconds += max(
                0.0,
                elapsed
                - (timing.routing_time_seconds - routing_before)
                - (timing.insertion_time_seconds - insertion_before)
                - (timing.movement_time_seconds - movement_before),
            )

        backlog = remaining
        movement_started = perf_counter()
        movement(local_couriers, [], batch_size, environment.station_set)
        timing.movement_time_seconds += perf_counter() - movement_started
        if progress_callback is not None:
            progress_callback(
                {
                    "phase": "batch_completed",
                    "detail": f"batch {batch_index}/{total_batches}",
                    "completed_units": batch_index,
                    "total_units": total_batches,
                    "unit_label": "batches",
                    "backlog_tasks": len(backlog),
                }
            )

    if accepted_assignments > 0:
        drain_legacy_routes(
            local_couriers=local_couriers,
            partner_couriers_by_platform={},
            station_set=environment.station_set,
            step_seconds=60,
            movement_callback=movement,
        )

    return {
        "TR": total_revenue,
        "CR": accepted_assignments / total_tasks,
        "BPT": timing.decision_time_seconds,
        "delivered_parcels": accepted_assignments,
        "accepted_assignments": accepted_assignments,
    }
