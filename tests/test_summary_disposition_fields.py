"""Regression for P5 disposition-aware summary keys (review_0512.md)."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from typing import Any, MutableSequence, Sequence
from unittest.mock import patch

from baselines.ramcom import run_ramcom_baseline_environment
from capa.models import CAPAConfig
from env.chengdu import ChengduBatchRuntime, prepare_chengdu_batch


def _no_movement(
    local_couriers: MutableSequence[Any],
    partner_couriers: MutableSequence[Any],
    step_seconds: int,
    station_set: Sequence[Any],
) -> None:
    """No-op movement callback for unit-level batch tests."""

    del local_couriers, partner_couriers, step_seconds, station_set


def _runtime(tasks: Sequence[Any], current_time: int = 0) -> ChengduBatchRuntime:
    """Build a minimal Chengdu batch runtime for disposition-counter tests."""

    return ChengduBatchRuntime(
        sorted_tasks=list(tasks),
        active_local_couriers=[],
        active_partner_by_platform={},
        station_set=[],
        travel_model=None,
        config=CAPAConfig(),
        movement=_no_movement,
        platform_base_prices={},
        platform_sharing_rates={},
        platform_qualities={},
        service_radius_meters=None,
        geo_index=None,
        speed_m_per_s=1.0,
        step_seconds=10,
        current_time=current_time,
    )


class ChengduRuntimeIntakeCounterTests(unittest.TestCase):
    """``prepare_chengdu_batch`` should increment ``expired_at_intake_count``."""

    def test_overdue_task_increments_intake_counter(self) -> None:
        already = SimpleNamespace(num="t1", s_time=0.0, d_time=5.0, weight=1.0, fare=1.0, l_node="A")
        fine = SimpleNamespace(num="t2", s_time=0.0, d_time=200.0, weight=1.0, fare=1.0, l_node="A")
        runtime = _runtime([already, fine], current_time=10)

        prepare_chengdu_batch(runtime, 5)

        self.assertEqual(runtime.expired_at_intake_count, 1)
        self.assertEqual(runtime.rejected_observed_deadline_count, 0)

    def test_no_increment_for_in_window_tasks(self) -> None:
        fresh = SimpleNamespace(num="t1", s_time=0.0, d_time=500.0, weight=1.0, fare=1.0, l_node="A")
        runtime = _runtime([fresh], current_time=0)

        prepare_chengdu_batch(runtime, 5)

        self.assertEqual(runtime.expired_at_intake_count, 0)


class RamComDispositionFieldsTests(unittest.TestCase):
    """RamCOM should emit four disposition keys in its returned summary."""

    def test_summary_contains_all_disposition_keys(self) -> None:
        task = SimpleNamespace(
            num="t1",
            fare=10.0,
            s_time=0.0,
            d_time=-1.0,
            weight=1.0,
            l_node="p1",
        )
        environment = SimpleNamespace(
            tasks=[task],
            local_couriers=[],
            partner_couriers_by_platform={},
            movement_callback=lambda *args, **kwargs: None,
            station_set=[],
            travel_model=SimpleNamespace(distance=lambda start, end: 0.0, travel_time=lambda start, end: 0.0),
            service_radius_km=None,
            geo_index=None,
            travel_speed_m_per_s=0.0,
        )

        with patch("baselines.ramcom.build_legacy_feasible_insertions", return_value=[]):
            result = run_ramcom_baseline_environment(environment=environment)

        for key in (
            "expired_at_intake",
            "accepted_but_timed_out",
            "rejected_observed_deadline",
            "expired_due_to_true_deadline",
        ):
            self.assertIn(key, result)
        self.assertEqual(result["expired_at_intake"], 1)
        self.assertEqual(result["accepted_but_timed_out"], 0)
        self.assertEqual(
            result["expired_due_to_true_deadline"],
            result["expired_at_intake"] + result["accepted_but_timed_out"],
        )

    def test_rejected_observed_deadline_counts_no_feasible(self) -> None:
        task = SimpleNamespace(
            num="t1",
            fare=10.0,
            s_time=0.0,
            d_time=120.0,
            weight=1.0,
            l_node="p1",
        )
        environment = SimpleNamespace(
            tasks=[task],
            local_couriers=[],
            partner_couriers_by_platform={},
            movement_callback=lambda *args, **kwargs: None,
            station_set=[],
            travel_model=SimpleNamespace(distance=lambda start, end: 0.0, travel_time=lambda start, end: 0.0),
            service_radius_km=None,
            geo_index=None,
            travel_speed_m_per_s=0.0,
        )

        with patch("baselines.ramcom.build_legacy_feasible_insertions", return_value=[]):
            result = run_ramcom_baseline_environment(environment=environment)

        self.assertEqual(result["expired_at_intake"], 0)
        self.assertEqual(result["rejected_observed_deadline"], 1)


if __name__ == "__main__":
    unittest.main()
