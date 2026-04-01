"""Shared feasibility constraints for CAPA and Chengdu baseline runners."""

from __future__ import annotations

from typing import Any


def is_within_service_radius(
    start_location: Any,
    task_location: Any,
    travel_model: Any,
    service_radius_meters: float | None,
) -> bool:
    """Return whether a courier-task pair respects the configured service radius.

    Args:
        start_location: Courier current location node identifier.
        task_location: Task pickup location node identifier.
        travel_model: Travel model exposing a `distance(start, end)` method.
        service_radius_meters: Maximum allowed courier-to-task distance in meters.

    Returns:
        `True` when the radius is disabled or the shortest-path distance is within the limit.
    """

    if service_radius_meters is None:
        return True
    return float(travel_model.distance(start_location, task_location)) <= float(service_radius_meters)
