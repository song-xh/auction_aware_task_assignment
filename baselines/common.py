"""Shared helpers for Chengdu-adapted baseline algorithms."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from capa.cama import is_feasible_local_match
from capa.config import DEFAULT_COURIER_ALPHA, DEFAULT_COURIER_BETA, DEFAULT_COURIER_SERVICE_SCORE
from capa.models import Courier
from capa.utility import GeoIndex, InsertionCache, TimedTravelModel, TimingAccumulator, find_best_local_insertion
from env.chengdu import LegacyCourierSnapshotCache, legacy_courier_to_capa, legacy_task_to_parcel


def mean_decision_time(total_seconds: float, decision_epochs: int) -> float:
    """Return mean assignment-decision time per comparable BPT epoch.

    Args:
        total_seconds: Accumulated assignment-decision time with routing,
            insertion, and movement excluded.
        decision_epochs: Number of task/batch/round epochs represented by the
            accumulated decision time.

    Returns:
        Mean decision time in seconds, or `0.0` when no decision epoch exists.
    """

    if decision_epochs <= 0:
        return 0.0
    return float(total_seconds) / float(decision_epochs)


def sum_delivered_assignment_revenue(
    accepted_revenues_by_task_id: Mapping[str, float],
    delivered_task_ids: Iterable[str],
) -> float:
    """Sum local-platform revenue only for accepted tasks that were delivered.

    Args:
        accepted_revenues_by_task_id: Revenue that would be realized for each
            accepted task if it leaves the courier route before the terminal
            deadline check.
        delivered_task_ids: Accepted task identifiers that were physically
            delivered after route progression.

    Returns:
        Total realized local-platform revenue for delivered tasks only.
    """

    return sum(
        float(accepted_revenues_by_task_id[task_id])
        for task_id in delivered_task_ids
        if task_id in accepted_revenues_by_task_id
    )


def summarize_realized_assignment_breakdown(
    delivered_task_ids: Iterable[str],
    assignment_modes_by_task_id: Mapping[str, str],
    partner_platform_by_task_id: Mapping[str, str] | None = None,
    partner_revenue_by_task_id: Mapping[str, float] | None = None,
) -> tuple[int, int, dict[str, int], dict[str, float]]:
    """Summarize delivered local/cross assignments and realized partner revenue.

    Args:
        delivered_task_ids: Accepted task identifiers completed on time.
        assignment_modes_by_task_id: Accepted assignment mode per task id.
        partner_platform_by_task_id: Optional winning partner platform per cross task id.
        partner_revenue_by_task_id: Optional realized partner payment per cross task id.

    Returns:
        ``(local_count, cross_count, partner_counts, partner_revenues)`` over
        the on-time delivered task set only.
    """

    local_count = 0
    cross_count = 0
    partner_counts: dict[str, int] = {}
    partner_revenues: dict[str, float] = {}
    for task_id in delivered_task_ids:
        mode = assignment_modes_by_task_id.get(task_id)
        if mode == "local":
            local_count += 1
            continue
        if mode != "cross":
            continue
        cross_count += 1
        platform_id = None if partner_platform_by_task_id is None else partner_platform_by_task_id.get(task_id)
        if platform_id is None:
            continue
        partner_counts[platform_id] = partner_counts.get(platform_id, 0) + 1
        if partner_revenue_by_task_id is not None and task_id in partner_revenue_by_task_id:
            partner_revenues[platform_id] = partner_revenues.get(platform_id, 0.0) + float(partner_revenue_by_task_id[task_id])
    return local_count, cross_count, partner_counts, partner_revenues


@dataclass(frozen=True)
class LegacyFeasibleInsertion:
    """Store one feasible courier-task insertion against the current Chengdu state.

    Args:
        courier: Legacy courier object from the shared Chengdu environment.
        parcel: Converted CAPA parcel snapshot for the task.
        insertion_index: Best route insertion index in the courier snapshot.
        distance_meters: Shortest-path distance from courier current location to parcel location.
    """

    courier: Any
    parcel: Any
    insertion_index: int
    distance_meters: float


def build_legacy_feasible_insertions(
    task: Any,
    couriers: Sequence[Any],
    travel_model: Any,
    now: int,
    service_radius_meters: float | None,
    courier_id_prefix: str,
    timing: TimingAccumulator | None = None,
    snapshot_cache: LegacyCourierSnapshotCache | None = None,
    insertion_cache: InsertionCache | None = None,
    geo_index: GeoIndex | None = None,
    speed_m_per_s: float = 0.0,
) -> list[LegacyFeasibleInsertion]:
    """Collect all current courier-task insertions that satisfy the shared Chengdu constraints.

    Args:
        task: Legacy Chengdu task object.
        couriers: Candidate legacy couriers.
        travel_model: Shared travel model.
        now: Current simulation time.
        service_radius_meters: Maximum courier-to-task service distance in meters, or `None`.
        courier_id_prefix: Stable prefix used when converting legacy couriers into CAPA snapshots.

    Returns:
        All feasible insertions for the provided task and courier pool.
    """

    parcel = legacy_task_to_parcel(task)
    timed_travel_model = TimedTravelModel(travel_model, timing)
    feasible: list[LegacyFeasibleInsertion] = []
    for courier in couriers:
        snapshot = project_courier_to_capa(
            courier,
            courier_id=f"{courier_id_prefix}-{getattr(courier, 'num')}",
            snapshot_cache=snapshot_cache,
        )
        if not is_feasible_local_match(
            parcel, snapshot, timed_travel_model, now,
            service_radius_meters=service_radius_meters,
            geo_index=geo_index,
            speed_m_per_s=speed_m_per_s,
        ):
            continue
        _, insertion_index = find_best_local_insertion(
            parcel,
            snapshot,
            timed_travel_model,
            timing=timing,
            insertion_cache=insertion_cache,
            geo_index=geo_index,
        )
        feasible.append(
            LegacyFeasibleInsertion(
                courier=courier,
                parcel=parcel,
                insertion_index=insertion_index,
                distance_meters=float(timed_travel_model.distance(getattr(courier, "location"), getattr(task, "l_node"))),
            )
        )
    return feasible


def extract_worker_history_values(courier: Any) -> list[float]:
    """Return the empirical history values used by RamCOM acceptance estimation.

    Args:
        courier: Legacy courier object or a test double.

    Returns:
        Historical completed-value samples. If the courier already exposes
        `history_completed_values`, that data is used directly. Otherwise the
        initial scheduled task fares are used as the worker history.
    """

    explicit_history = getattr(courier, "history_completed_values", None)
    if explicit_history is not None:
        return [float(value) for value in explicit_history]
    return [float(getattr(task, "fare", 0.0)) for task in getattr(courier, "re_schedule", []) if hasattr(task, "fare")]


def project_courier_to_capa(
    courier: Any,
    courier_id: str,
    snapshot_cache: LegacyCourierSnapshotCache | None = None,
) -> Courier:
    """Project a legacy courier or a light-weight test double into the CAPA courier model."""
    try:
        if snapshot_cache is not None:
            return snapshot_cache.get(courier, courier_id=courier_id)
        return legacy_courier_to_capa(courier, courier_id=courier_id)
    except ValueError:
        return Courier(
            courier_id=courier_id,
            current_location=getattr(courier, "location"),
            depot_location=getattr(courier, "location"),
            capacity=float(getattr(courier, "max_weight")),
            current_load=float(getattr(courier, "re_weight", 0.0)),
            route_locations=[getattr(task, "l_node") for task in getattr(courier, "re_schedule", [])],
            available_from=0,
            alpha=float(getattr(courier, "w", DEFAULT_COURIER_ALPHA)),
            beta=float(getattr(courier, "c", DEFAULT_COURIER_BETA)),
            service_score=float(getattr(courier, "service_score", DEFAULT_COURIER_SERVICE_SCORE)),
        )
