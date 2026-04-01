"""Metric helpers for the paper's Phase 4 evaluation surface."""

from __future__ import annotations

from typing import Sequence

from .models import Assignment, BatchReport, RunMetrics


def compute_total_revenue(assignments: Sequence[Assignment]) -> float:
    """Compute the paper's total revenue metric TR."""
    return sum(item.local_platform_revenue for item in assignments)


def compute_completion_rate(assignments: Sequence[Assignment], total_parcels: int) -> float:
    """Compute the paper's completion-rate metric CR."""
    if total_parcels <= 0:
        return 0.0
    return len(assignments) / total_parcels


def compute_batch_processing_time(batch_reports: Sequence[BatchReport]) -> float:
    """Compute the aggregate batch-processing-time metric BPT."""
    return sum(report.timing.decision_time_seconds for report in batch_reports)


def build_run_metrics(
    assignments: Sequence[Assignment],
    total_parcels: int,
    batch_reports: Sequence[BatchReport],
    delivered_parcel_count: int | None = None,
) -> RunMetrics:
    """Assemble the Phase 4 metrics, allowing delivery-based completion accounting."""
    delivered_count = len(assignments) if delivered_parcel_count is None else delivered_parcel_count
    return RunMetrics(
        total_revenue=compute_total_revenue(assignments),
        completion_rate=compute_completion_rate([None] * delivered_count, total_parcels),
        batch_processing_time=compute_batch_processing_time(batch_reports),
        delivered_parcel_count=delivered_count,
        accepted_parcel_count=len(assignments),
        excluded_routing_time=sum(report.timing.routing_time_seconds for report in batch_reports),
        excluded_insertion_time=sum(report.timing.insertion_time_seconds for report in batch_reports),
        excluded_movement_time=sum(report.timing.movement_time_seconds for report in batch_reports),
    )
