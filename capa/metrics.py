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
    return sum(report.processing_time_seconds for report in batch_reports)


def build_run_metrics(assignments: Sequence[Assignment], total_parcels: int, batch_reports: Sequence[BatchReport]) -> RunMetrics:
    """Assemble the three Phase 4 metrics into one immutable record."""
    return RunMetrics(
        total_revenue=compute_total_revenue(assignments),
        completion_rate=compute_completion_rate(assignments, total_parcels),
        batch_processing_time=compute_batch_processing_time(batch_reports),
    )
