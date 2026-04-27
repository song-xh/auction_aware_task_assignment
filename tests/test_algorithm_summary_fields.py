"""Tests for unified experiment summary payload enrichment."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from algorithms.basegta_runner import BaseGTARunner
from algorithms.capa_runner import CAPAAlgorithmRunner
from algorithms.greedy_runner import GreedyAlgorithmRunner
from capa.models import Assignment, BatchReport, CAPAResult, CAPAConfig, Courier, Parcel, RunMetrics


def _task(task_id: str) -> SimpleNamespace:
    """Build one minimal legacy task used only for environment cardinality."""

    return SimpleNamespace(num=task_id, s_time=0.0)


def _environment() -> SimpleNamespace:
    """Build one synthetic unified environment for summary tests."""

    return SimpleNamespace(
        tasks=[_task("t1"), _task("t2"), _task("t3")],
        local_couriers=[],
        partner_couriers_by_platform={"P1": [], "P2": []},
        partner_tasks_by_platform={"P1": [_task("p1"), _task("p2")], "P2": [_task("p3"), _task("p4"), _task("p5")]},
        station_set=[],
        travel_model=SimpleNamespace(),
        platform_base_prices={"P1": 1.0, "P2": 1.5},
        platform_sharing_rates={"P1": 0.5, "P2": 0.6},
        platform_qualities={"P1": 1.0, "P2": 0.9},
        movement_callback=lambda *args, **kwargs: None,
        service_radius_km=None,
        geo_index=None,
        travel_speed_m_per_s=0.0,
    )


def _capa_result() -> CAPAResult:
    """Build one minimal CAPA result with one local and one cross assignment."""

    local_parcel = Parcel(parcel_id="t1", location="A", arrival_time=0, deadline=300, weight=1.0, fare=10.0)
    cross_parcel = Parcel(parcel_id="t2", location="B", arrival_time=0, deadline=300, weight=1.0, fare=12.0)
    unresolved_parcel = Parcel(parcel_id="t3", location="C", arrival_time=0, deadline=300, weight=1.0, fare=8.0)
    local_courier = Courier(courier_id="local-1", current_location="L", depot_location="D", capacity=5.0)
    partner_courier = Courier(courier_id="partner-1", current_location="P", depot_location="Q", capacity=5.0)
    local_assignment = Assignment(
        parcel=local_parcel,
        courier=local_courier,
        mode="local",
        platform_id=None,
        courier_payment=2.0,
        platform_payment=0.0,
        local_platform_revenue=8.0,
        cooperating_platform_revenue=0.0,
        courier_revenue=2.0,
    )
    cross_assignment = Assignment(
        parcel=cross_parcel,
        courier=partner_courier,
        mode="cross",
        platform_id="P1",
        courier_payment=3.0,
        platform_payment=4.5,
        local_platform_revenue=7.5,
        cooperating_platform_revenue=4.5,
        courier_revenue=3.0,
    )
    batch_report = BatchReport(
        batch_index=1,
        batch_time=30,
        input_parcels=[local_parcel, cross_parcel, unresolved_parcel],
        local_assignments=[local_assignment],
        cross_assignments=[cross_assignment],
        unresolved_parcels=[unresolved_parcel],
        processing_time_seconds=0.05,
        delivered_parcel_count=2,
    )
    return CAPAResult(
        matching_plan=[local_assignment, cross_assignment],
        unassigned_parcels=[unresolved_parcel],
        batch_reports=[batch_report],
        metrics=RunMetrics(
            total_revenue=15.5,
            completion_rate=2 / 3,
            batch_processing_time=0.05,
            delivered_parcel_count=2,
            accepted_parcel_count=2,
        ),
        delivered_parcels=[local_parcel, cross_parcel],
    )


def test_capa_runner_summary_exposes_assignment_and_partner_stats() -> None:
    """CAPA summary should include unified assignment, partner, and timing metadata."""

    environment = _environment()
    runner = CAPAAlgorithmRunner(batch_size=30)

    with patch("algorithms.capa_runner.run_time_stepped_chengdu_batches", return_value=_capa_result()):
        summary = runner.run(environment=environment)

    assert summary["metrics"]["TR"] == 15.5
    assert summary["assignment_stats"]["local_platform"]["local_matches"] == 1
    assert summary["assignment_stats"]["local_platform"]["cross_platform_matches"] == 1
    assert summary["assignment_stats"]["local_platform"]["unresolved_parcels"] == 1
    assert summary["assignment_stats"]["cooperating_platforms"]["P1"]["own_task_count"] == 2
    assert summary["assignment_stats"]["cooperating_platforms"]["P1"]["accepted_cross_platform_tasks"] == 1
    assert summary["assignment_stats"]["cooperating_platforms"]["P1"]["cooperative_revenue"] == 4.5
    assert "started_at" in summary["timing"]
    assert "finished_at" in summary["timing"]
    assert summary["timing"]["duration_seconds"] >= 0.0


def test_basegta_runner_summary_propagates_cross_platform_breakdown() -> None:
    """GTA-family summaries should expose partner cross-task counts and revenues."""

    environment = _environment()
    runner = BaseGTARunner(
        baseline_runner=lambda **kwargs: {
            "TR": 11.0,
            "CR": 2 / 3,
            "BPT": 0.04,
            "delivered_parcels": 2,
            "accepted_assignments": 2,
            "local_assignment_count": 1,
            "cross_assignment_count": 1,
            "unresolved_parcel_count": 1,
            "partner_cross_assignment_counts": {"P2": 1},
            "partner_cross_revenues": {"P2": 6.0},
        }
    )

    summary = runner.run(environment=environment)

    assert summary["assignment_stats"]["local_platform"]["local_matches"] == 1
    assert summary["assignment_stats"]["local_platform"]["cross_platform_matches"] == 1
    assert summary["assignment_stats"]["cooperating_platforms"]["P2"]["accepted_cross_platform_tasks"] == 1
    assert summary["assignment_stats"]["cooperating_platforms"]["P2"]["cooperative_revenue"] == 6.0


def test_greedy_runner_summary_defaults_to_local_only_breakdown() -> None:
    """Local-only baselines should still emit the unified summary shape."""

    environment = _environment()
    runner = GreedyAlgorithmRunner(
        batch_size=30,
        baseline_runner=lambda **kwargs: {
            "TR": 8.0,
            "CR": 2 / 3,
            "BPT": 0.03,
            "delivered_parcels": 2,
            "accepted_assignments": 2,
        },
    )

    summary = runner.run(environment=environment)

    assert summary["assignment_stats"]["local_platform"]["local_matches"] == 2
    assert summary["assignment_stats"]["local_platform"]["cross_platform_matches"] == 0
    assert summary["assignment_stats"]["local_platform"]["unresolved_parcels"] == 1
    assert summary["assignment_stats"]["cooperating_platforms"]["P1"]["accepted_cross_platform_tasks"] == 0
    assert summary["assignment_stats"]["cooperating_platforms"]["P1"]["cooperative_revenue"] == 0.0
