"""Tests for MRA BPT accounting."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from baselines.mra import run_mra_baseline_environment


class MRABPTTest(unittest.TestCase):
    """Verify MRA reports the CAPA-aligned decision-time metric."""

    def test_run_mra_reports_decision_time_seconds(self) -> None:
        """BPT should come from ``timing.decision_time_seconds`` rather than a local accumulator."""

        task = SimpleNamespace(num="t1", fare=10.0, s_time=0.0)
        courier = SimpleNamespace(num=1)
        environment = SimpleNamespace(
            tasks=[task],
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
            patch("baselines.mra.group_legacy_tasks_by_batch", return_value=[[task]]),
            patch("baselines.mra.build_legacy_feasible_insertions", side_effect=fake_feasible_insertions),
            patch("baselines.mra.compute_mra_bid", return_value=1.0),
            patch("baselines.mra.compute_local_platform_revenue_for_local_completion", return_value=5.0),
            patch("baselines.mra.apply_assignment_to_legacy_courier"),
            patch("baselines.mra.drain_legacy_routes"),
            patch("baselines.mra.perf_counter", side_effect=[0.0, 8.0, 9.0, 10.0]),
        ):
            result = run_mra_baseline_environment(environment=environment, batch_size=30)

        self.assertEqual(len(timing_instances), 1)
        self.assertEqual(timing_instances[0].decision_time_seconds, 3.0)
        self.assertEqual(result["BPT"], timing_instances[0].decision_time_seconds)


if __name__ == "__main__":
    unittest.main()
