"""Shared feasibility constraints for CAPA and Chengdu baseline runners."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .utility import GeoIndex


def is_within_service_radius(
    start_location: Any,
    task_location: Any,
    travel_model: Any,
    service_radius_meters: float | None,
    geo_index: GeoIndex | None = None,
) -> bool:
    """Return whether a courier-task pair respects the configured service radius.

    When *geo_index* is provided the Haversine straight-line distance is
    checked first.  If the lower bound already exceeds the radius the
    expensive road-network query is skipped entirely.
    """

    if service_radius_meters is None:
        return True
    if geo_index is not None:
        lb = geo_index.haversine_meters_between(start_location, task_location)
        if lb is not None and lb > service_radius_meters:
            return False
    return float(travel_model.distance(start_location, task_location)) <= float(service_radius_meters)


def is_within_service_radius_by_geo(
    start_location: Any,
    task_location: Any,
    service_radius_meters: float | None,
    geo_index: GeoIndex | None = None,
) -> bool:
    """Return whether a pair survives the geo lower-bound radius filter."""

    if service_radius_meters is None or geo_index is None:
        return True
    lb = geo_index.haversine_meters_between(start_location, task_location)
    if lb is None:
        return True
    return lb <= float(service_radius_meters)


def is_deadline_feasible_by_geo(
    courier_location: Any,
    task_location: Any,
    now: int,
    deadline: float,
    speed_m_per_s: float,
    geo_index: GeoIndex | None = None,
) -> bool:
    """Quick geometric check: can the courier possibly reach the task before deadline?

    Returns ``True`` (optimistic) when the geo_index is unavailable or the
    straight-line lower bound allows it.  Returns ``False`` only when it is
    *certain* the courier cannot arrive in time.
    """

    if geo_index is None or speed_m_per_s <= 0:
        return True
    lb = geo_index.haversine_meters_between(courier_location, task_location)
    if lb is None:
        return True
    return now + lb / speed_m_per_s <= deadline
