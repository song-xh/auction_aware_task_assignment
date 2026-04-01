"""Shared helpers for Chengdu-adapted baseline algorithms."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from capa.cama import is_feasible_local_match
from capa.models import Courier
from capa.utility import find_best_local_insertion
from env.chengdu import legacy_courier_to_capa, legacy_task_to_parcel


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
    feasible: list[LegacyFeasibleInsertion] = []
    for courier in couriers:
        snapshot = project_courier_to_capa(courier, courier_id=f"{courier_id_prefix}-{getattr(courier, 'num')}")
        if not is_feasible_local_match(parcel, snapshot, travel_model, now, service_radius_meters=service_radius_meters):
            continue
        _, insertion_index = find_best_local_insertion(parcel, snapshot, travel_model)
        feasible.append(
            LegacyFeasibleInsertion(
                courier=courier,
                parcel=parcel,
                insertion_index=insertion_index,
                distance_meters=float(travel_model.distance(getattr(courier, "location"), getattr(task, "l_node"))),
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


def project_courier_to_capa(courier: Any, courier_id: str) -> Courier:
    """Project a legacy courier or a light-weight test double into the CAPA courier model."""
    try:
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
            alpha=float(getattr(courier, "w", 0.5)),
            beta=float(getattr(courier, "c", 0.5)),
            service_score=float(getattr(courier, "service_score", 0.8)),
        )
