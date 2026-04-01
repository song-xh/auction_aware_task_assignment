"""Shared timing breakdown models used by CAPA metrics and experiment outputs."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BatchTimingBreakdown:
    """Record decision and excluded timing components for one matching round."""

    decision_time_seconds: float = 0.0
    routing_time_seconds: float = 0.0
    insertion_time_seconds: float = 0.0
    movement_time_seconds: float = 0.0
