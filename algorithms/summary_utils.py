"""Shared helpers for enriched Chengdu experiment summary payloads."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable, Mapping, Sequence


def build_decision_trace(
    delivered_assignments: Sequence[Any] = (),
    timed_out_assignments: Sequence[Any] = (),
    unassigned_parcel_ids: Iterable[str] = (),
) -> list[dict[str, Any]]:
    """Project per-parcel decision outcomes into one comparison-friendly list.

    Args:
        delivered_assignments: Accepted assignments completed on time.
        timed_out_assignments: Accepted assignments that completed after the
            true deadline.
        unassigned_parcel_ids: Parcel ids never accepted by the algorithm.

    Returns:
        List of entries with stable keys ``parcel_id``, ``mode``,
        ``courier_id``, ``delivered``, ``on_time``, ``local_platform_revenue``.
        Modes are ``"local"`` / ``"cross"`` for accepted parcels and
        ``"unmatched"`` for unassigned parcels.
    """

    trace: list[dict[str, Any]] = []
    for assignment in delivered_assignments:
        trace.append(_assignment_to_trace(assignment, delivered=True, on_time=True))
    for assignment in timed_out_assignments:
        trace.append(_assignment_to_trace(assignment, delivered=False, on_time=False))
    for parcel_id in unassigned_parcel_ids:
        trace.append(
            {
                "parcel_id": str(parcel_id),
                "mode": "unmatched",
                "courier_id": None,
                "delivered": False,
                "on_time": False,
                "local_platform_revenue": 0.0,
            }
        )
    return trace


def _assignment_to_trace(assignment: Any, delivered: bool, on_time: bool) -> dict[str, Any]:
    """Convert one Assignment into a trace dict; ``on_time`` mirrors delivery success."""

    parcel = getattr(assignment, "parcel", None)
    courier = getattr(assignment, "courier", None)
    return {
        "parcel_id": str(getattr(parcel, "parcel_id", "")),
        "mode": str(getattr(assignment, "mode", "")),
        "courier_id": None if courier is None else str(getattr(courier, "courier_id", "")),
        "delivered": bool(delivered),
        "on_time": bool(on_time),
        "local_platform_revenue": float(getattr(assignment, "local_platform_revenue", 0.0)),
    }


def build_algorithm_summary(
    algorithm: str,
    environment: Any,
    metrics: Mapping[str, Any],
    *,
    local_assignment_count: int | None = None,
    cross_assignment_count: int | None = None,
    unresolved_parcel_count: int | None = None,
    partner_cross_assignment_counts: Mapping[str, int] | None = None,
    partner_cross_revenues: Mapping[str, float] | None = None,
    started_at: datetime,
    finished_at: datetime,
    extra_fields: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one enriched, JSON-serializable experiment summary payload.

    Args:
        algorithm: Canonical algorithm name.
        environment: Prepared environment used by the runner.
        metrics: Normalized metric payload containing at least `TR`, `CR`, and `BPT`.
        local_assignment_count: Optional local-platform local completion count.
        cross_assignment_count: Optional local-platform cross-platform completion count.
        unresolved_parcel_count: Optional unresolved local task count.
        partner_cross_assignment_counts: Optional partner accepted cross-task counts.
        partner_cross_revenues: Optional realized partner revenues after sharing.
        started_at: Wall-clock start timestamp.
        finished_at: Wall-clock finish timestamp.
        extra_fields: Optional additional summary fields such as algorithm config.

    Returns:
        One enriched summary payload used by experiment runners and persisted to JSON.
    """

    accepted_assignments = int(metrics.get("accepted_assignments", 0))
    delivered_parcels = int(metrics.get("delivered_parcels", 0))
    timed_out_parcels = int(metrics.get("timed_out_parcels", 0))
    resolved_local_assignments = accepted_assignments if local_assignment_count is None else int(local_assignment_count)
    resolved_cross_assignments = 0 if cross_assignment_count is None else int(cross_assignment_count)
    total_tasks = len(list(getattr(environment, "tasks", [])))
    resolved_unresolved = max(
        0,
        total_tasks - resolved_local_assignments - resolved_cross_assignments,
    ) if unresolved_parcel_count is None else int(unresolved_parcel_count)

    partner_counts = {
        str(platform_id): int(count)
        for platform_id, count in (partner_cross_assignment_counts or {}).items()
    }
    partner_revenues = {
        str(platform_id): float(revenue)
        for platform_id, revenue in (partner_cross_revenues or {}).items()
    }
    partner_task_streams = getattr(environment, "partner_tasks_by_platform", {}) or {}
    partner_platform_ids = _collect_partner_platform_ids(
        environment=environment,
        partner_cross_assignment_counts=partner_counts,
        partner_cross_revenues=partner_revenues,
    )
    partner_stats = {
        platform_id: {
            "own_task_count": len(list(partner_task_streams.get(platform_id, []))),
            "accepted_cross_platform_tasks": int(partner_counts.get(platform_id, 0)),
            "cooperative_revenue": float(partner_revenues.get(platform_id, 0.0)),
        }
        for platform_id in partner_platform_ids
    }

    summary = {
        "algorithm": algorithm,
        "metrics": dict(metrics),
        "assignment_stats": {
            "local_platform": {
                "local_matches": resolved_local_assignments,
                "cross_platform_matches": resolved_cross_assignments,
                "unresolved_parcels": resolved_unresolved,
                "accepted_parcels": accepted_assignments,
                "delivered_parcels": delivered_parcels,
                "timed_out_parcels": timed_out_parcels,
            },
            "cooperating_platforms": partner_stats,
        },
        "timing": {
            "started_at": started_at.astimezone().isoformat(timespec="seconds"),
            "finished_at": finished_at.astimezone().isoformat(timespec="seconds"),
            "duration_seconds": max(0.0, (finished_at - started_at).total_seconds()),
        },
    }
    if extra_fields:
        summary.update(dict(extra_fields))
    return summary


def _collect_partner_platform_ids(
    *,
    environment: Any,
    partner_cross_assignment_counts: Mapping[str, int],
    partner_cross_revenues: Mapping[str, float],
) -> list[str]:
    """Collect the stable platform ordering used by enriched experiment summaries."""

    ordered: list[str] = []

    def extend(items: Any) -> None:
        """Append new stable platform identifiers while preserving first-seen order."""

        for item in items:
            platform_id = str(item)
            if platform_id not in ordered:
                ordered.append(platform_id)

    extend((getattr(environment, "partner_couriers_by_platform", {}) or {}).keys())
    extend((getattr(environment, "partner_tasks_by_platform", {}) or {}).keys())
    extend(partner_cross_assignment_counts.keys())
    extend(partner_cross_revenues.keys())
    return ordered
