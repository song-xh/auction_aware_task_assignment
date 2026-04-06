"""End-to-end CAPA batch runner for Algorithm 1."""

from __future__ import annotations

from collections import defaultdict
from time import perf_counter
from typing import DefaultDict, Dict, List, Sequence, Tuple

from .cama import run_cama
from .dapa import run_dapa
from .metrics import build_run_metrics
from .models import (
    BatchReport,
    CAPAConfig,
    CAPAResult,
    CooperatingPlatform,
    Courier,
    Parcel,
)
from .utility import DistanceMatrixTravelModel


def index_arrivals_by_time(parcels: Sequence[Parcel]) -> DefaultDict[int, List[Parcel]]:
    """Group parcels by arrival time for the online CAPA runner."""
    arrivals: DefaultDict[int, List[Parcel]] = defaultdict(list)
    for parcel in parcels:
        arrivals[parcel.arrival_time].append(parcel)
    return arrivals


def process_batch(
    batch_index: int,
    now: int,
    batch_parcels: Sequence[Parcel],
    local_couriers: Sequence[Courier],
    platforms: Sequence[CooperatingPlatform],
    travel_model: DistanceMatrixTravelModel,
    config: CAPAConfig,
) -> Tuple[BatchReport, List[Parcel]]:
    """Run CAMA then DAPA for a single CAPA batch and return unresolved parcels."""
    started_at = perf_counter()
    cama_result = run_cama(batch_parcels, local_couriers, travel_model, config, now=now)
    dapa_result = run_dapa(cama_result.auction_pool, platforms, travel_model, config, now=now)
    processing_time = perf_counter() - started_at
    report = BatchReport(
        batch_index=batch_index,
        batch_time=now,
        input_parcels=list(batch_parcels),
        local_assignments=list(cama_result.local_assignments),
        cross_assignments=list(dapa_result.cross_assignments),
        unresolved_parcels=list(dapa_result.unassigned_parcels),
        processing_time_seconds=processing_time,
        delivered_parcel_count=len(cama_result.local_assignments) + len(dapa_result.cross_assignments),
    )
    return report, list(dapa_result.unassigned_parcels)


def run_capa(
    parcels: Sequence[Parcel],
    local_couriers: Sequence[Courier],
    platforms: Sequence[CooperatingPlatform],
    travel_model: DistanceMatrixTravelModel,
    config: CAPAConfig,
    timeline_end: int | None = None,
) -> CAPAResult:
    """Run Algorithm 1 with batch accumulation, local matching, and cross-platform auctioning."""
    if config.batch_size <= 0:
        raise ValueError("Batch size must be positive.")
    if not parcels:
        empty_reports: List[BatchReport] = []
        return CAPAResult(
            matching_plan=[],
            unassigned_parcels=[],
            batch_reports=empty_reports,
            metrics=build_run_metrics([], 0, empty_reports),
        )

    arrivals = index_arrivals_by_time(parcels)
    current_time = min(parcel.arrival_time for parcel in parcels)
    terminal_time = max(parcel.arrival_time for parcel in parcels)
    if timeline_end is not None:
        terminal_time = max(terminal_time, timeline_end)

    matching_plan = []
    batch_reports: List[BatchReport] = []
    batch_buffer: List[Parcel] = []
    t_cum = 0
    batch_index = 0

    while current_time <= terminal_time:
        batch_buffer.extend(arrivals.get(current_time, []))
        t_cum += 1
        if t_cum == config.batch_size:
            batch_index += 1
            report, unresolved = process_batch(
                batch_index=batch_index,
                now=current_time,
                batch_parcels=batch_buffer,
                local_couriers=local_couriers,
                platforms=platforms,
                travel_model=travel_model,
                config=config,
            )
            batch_reports.append(report)
            matching_plan.extend(report.local_assignments)
            matching_plan.extend(report.cross_assignments)
            batch_buffer = list(unresolved)
            t_cum = 0
        current_time += 1

    if batch_buffer:
        batch_index += 1
        report, unresolved = process_batch(
            batch_index=batch_index,
            now=terminal_time,
            batch_parcels=batch_buffer,
            local_couriers=local_couriers,
            platforms=platforms,
            travel_model=travel_model,
            config=config,
        )
        batch_reports.append(report)
        matching_plan.extend(report.local_assignments)
        matching_plan.extend(report.cross_assignments)
        batch_buffer = list(unresolved)

    return CAPAResult(
        matching_plan=matching_plan,
        unassigned_parcels=batch_buffer,
        batch_reports=batch_reports,
        metrics=build_run_metrics(matching_plan, len(parcels), batch_reports),
    )
