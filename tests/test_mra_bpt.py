"""Tests for MRA BPT accounting."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from baselines.mra import run_mra_baseline_environment


class MRABPTTest(unittest.TestCase):
    """Verify MRA reports the CAPA-aligned decision-time metric."""

    def test_run_mra_reports_mean_decision_time_seconds(self) -> None:
        """BPT should be mean assignment-decision time over MRA decision epochs."""

        task = SimpleNamespace(num="t1", fare=10.0, s_time=0.0, d_time=300.0)
        task_two = SimpleNamespace(num="t2", fare=10.0, s_time=30.0, d_time=330.0)
        courier = SimpleNamespace(num=1)
        environment = SimpleNamespace(
            tasks=[task, task_two],
            local_couriers=[courier],
            movement_callback=lambda *args, **kwargs: None,
            station_set=[],
            travel_model=SimpleNamespace(distance=lambda start, end: 0.0, travel_time=lambda start, end: 0.0),
            service_radius_km=None,
        )
        timing_instances: list[SimpleNamespace] = []

        class FakeTimingAccumulator:
            """Minimal timing accumulator used to observe MRA's BPT source."""

            def __init__(self) -> None:
                self.decision_time_seconds = 0.0
                self.routing_time_seconds = 0.0
                self.insertion_time_seconds = 0.0
                self.movement_time_seconds = 0.0
                timing_instances.append(self)

        def fake_feasible_insertions(**kwargs):
            timing = kwargs["timing"]
            timing.routing_time_seconds += 3.0
            timing.insertion_time_seconds += 2.0
            return [SimpleNamespace(courier=courier, insertion_index=0, distance_meters=1.0)]

        with (
            patch("baselines.mra.TimingAccumulator", FakeTimingAccumulator),
            patch("baselines.mra.bucketize_legacy_tasks_by_batch", return_value=(0, {0: [task], 1: [task_two]})),
            patch("baselines.mra.build_legacy_feasible_insertions", side_effect=fake_feasible_insertions),
            patch("baselines.mra.compute_mra_bid", return_value=1.0),
            patch("baselines.mra.compute_local_platform_revenue_for_local_completion", return_value=5.0),
            patch("baselines.mra.apply_assignment_to_legacy_courier"),
            patch("baselines.mra.drain_legacy_routes_with_deadline_accounting"),
            patch("baselines.mra.perf_counter", side_effect=[0.0, 0.0, 10.0, 18.0, 20.0, 20.0, 30.0, 38.0]),
        ):
            result = run_mra_baseline_environment(environment=environment, batch_size=30)

        self.assertEqual(len(timing_instances), 1)
        self.assertEqual(timing_instances[0].decision_time_seconds, 6.0)
        self.assertEqual(result["BPT"], 3.0)

    def test_run_mra_matches_batch_tasks_at_batch_end(self) -> None:
        """MRA should evaluate every batch task after the full batch wait time."""

        early = SimpleNamespace(num="early", fare=10.0, s_time=0.0, d_time=180.0, weight=1.0, l_node="p1")
        late = SimpleNamespace(num="late", fare=10.0, s_time=29.0, d_time=209.0, weight=1.0, l_node="p2")
        courier = SimpleNamespace(num=1, location="start", re_schedule=[], re_weight=0.0, max_weight=5.0)
        environment = SimpleNamespace(
            tasks=[early, late],
            local_couriers=[courier],
            movement_callback=lambda *args, **kwargs: None,
            station_set=[],
            travel_model=SimpleNamespace(distance=lambda start, end: 0.0, travel_time=lambda start, end: 0.0),
            service_radius_km=None,
            geo_index=None,
            travel_speed_m_per_s=0.0,
        )
        observed_now: list[int] = []

        def fake_feasible_insertions(**kwargs):
            observed_now.append(kwargs["now"])
            return [SimpleNamespace(courier=courier, insertion_index=0, distance_meters=1.0)]

        with (
            patch("baselines.mra.build_legacy_feasible_insertions", side_effect=fake_feasible_insertions),
            patch("baselines.mra.compute_mra_bid", return_value=1.0),
            patch("baselines.mra.apply_assignment_to_legacy_courier"),
            patch("baselines.mra.drain_legacy_routes_with_deadline_accounting"),
        ):
            run_mra_baseline_environment(environment=environment, batch_size=30)

        self.assertGreaterEqual(len(observed_now), 2)
        self.assertTrue(all(now == 30 for now in observed_now))

    def test_run_mra_expires_tasks_before_batch_end_matching(self) -> None:
        """MRA should not match a task whose true deadline expires during batch wait."""

        expired = SimpleNamespace(num="expired", fare=10.0, s_time=29.0, d_time=29.0, weight=1.0, l_node="p1")
        courier = SimpleNamespace(num=1, location="start", re_schedule=[], re_weight=0.0, max_weight=5.0)
        environment = SimpleNamespace(
            tasks=[expired],
            local_couriers=[courier],
            movement_callback=lambda *args, **kwargs: None,
            station_set=[],
            travel_model=SimpleNamespace(distance=lambda start, end: 0.0, travel_time=lambda start, end: 0.0),
            service_radius_km=None,
            geo_index=None,
            travel_speed_m_per_s=0.0,
        )

        with patch("baselines.mra.build_legacy_feasible_insertions") as feasible:
            result = run_mra_baseline_environment(environment=environment, batch_size=30)

        feasible.assert_not_called()
        self.assertEqual(result["accepted_assignments"], 0)
        self.assertEqual(result["delivered_parcels"], 0)
        self.assertEqual(result["unresolved_parcel_count"], 1)


if __name__ == "__main__":
    unittest.main()
