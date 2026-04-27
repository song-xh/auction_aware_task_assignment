"""Shared helpers for enriched Chengdu experiment summary payloads."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping


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
