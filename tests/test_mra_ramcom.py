"""Tests for the MRA and RamCOM baseline implementations."""

from __future__ import annotations

import random
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from env.chengdu import ChengduEnvironment


class _LinearTravelModel:
    """Provide deterministic distances and travel times for baseline tests."""

    def distance(self, start, end) -> float:
        """Return an absolute-distance metric in meters."""
        return float(abs(end - start))

    def travel_time(self, start, end) -> float:
        """Return the same linear metric as travel time in seconds."""
        return float(abs(end - start))


class MRARamCOMTests(unittest.TestCase):
    """Validate the new cooperative and multi-round baseline behaviors."""

    @staticmethod
    def _drain_one_step(local, partner, seconds, station_set) -> None:
        """Pop one queued task per courier so drain-based tests can terminate."""
        for courier in [*local, *partner]:
            if getattr(courier, "re_schedule", []):
                courier.re_schedule.pop(0)

    def test_mra_multi_round_assignment_produces_nonzero_metrics(self) -> None:
        """MRA should assign feasible parcels over multiple rounds and return normalized metrics."""
        from baselines.mra import run_mra_baseline_environment

        environment = ChengduEnvironment(
            tasks=[
                SimpleNamespace(num="t1", l_node=1, s_time=0, d_time=100, weight=1.0, fare=10.0),
                SimpleNamespace(num="t2", l_node=3, s_time=0, d_time=100, weight=1.0, fare=12.0),
            ],
            local_couriers=[
                SimpleNamespace(num=1, location=0, re_schedule=[], re_weight=0.0, max_weight=5.0),
                SimpleNamespace(num=2, location=4, re_schedule=[], re_weight=0.0, max_weight=5.0),
            ],
            partner_couriers_by_platform={},
            station_set=[],
            travel_model=_LinearTravelModel(),
            platform_base_prices={},
            platform_sharing_rates={},
            platform_qualities={},
            service_radius_km=1.0,
            movement_callback=self._drain_one_step,
        )

        metrics = run_mra_baseline_environment(environment=environment, batch_size=60)

        self.assertGreater(metrics["TR"], 0.0)
        self.assertGreater(metrics["CR"], 0.0)
        self.assertEqual(metrics["delivered_parcels"], 2)

    def test_ramcom_payment_search_prefers_positive_expected_revenue(self) -> None:
        """RamCOM should select an outer payment that maximizes expected cooperative revenue."""
        from baselines.ramcom import choose_outer_payment_by_expected_revenue

        request = SimpleNamespace(fare=10.0)
        outer_histories = [[2.0, 4.0, 8.0], [3.0, 5.0, 9.0]]

        payment = choose_outer_payment_by_expected_revenue(request=request, outer_worker_histories=outer_histories)

        self.assertGreater(payment, 0.0)
        self.assertLessEqual(payment, 10.0)

    def test_ramcom_online_matching_produces_nonzero_metrics(self) -> None:
        """RamCOM should produce nonzero output on a small Chengdu-style environment under a fixed seed."""
        from baselines.ramcom import run_ramcom_baseline_environment

        environment = ChengduEnvironment(
            tasks=[
                SimpleNamespace(num="t1", l_node=1, s_time=0, d_time=100, weight=1.0, fare=10.0),
                SimpleNamespace(num="t2", l_node=3, s_time=1, d_time=100, weight=1.0, fare=12.0),
            ],
            local_couriers=[
                SimpleNamespace(num=1, location=0, re_schedule=[], re_weight=0.0, max_weight=5.0, history_completed_values=[3.0, 5.0]),
            ],
            partner_couriers_by_platform={
                "P1": [
                    SimpleNamespace(num=2, location=2, re_schedule=[], re_weight=0.0, max_weight=5.0, history_completed_values=[2.0, 4.0, 6.0])
                ]
            },
            station_set=[],
            travel_model=_LinearTravelModel(),
            platform_base_prices={"P1": 1.0},
            platform_sharing_rates={"P1": 0.4},
            platform_qualities={"P1": 1.0},
            service_radius_km=1.0,
            movement_callback=self._drain_one_step,
        )

        metrics = run_ramcom_baseline_environment(environment=environment, random_seed=7)

        self.assertGreater(metrics["TR"], 0.0)
        self.assertGreater(metrics["CR"], 0.0)
        self.assertGreater(metrics["accepted_assignments"], 0)

    def test_registry_and_runner_support_mra_and_ramcom(self) -> None:
        """The unified algorithm registry should expose MRA and RamCOM with the standard runner contract."""
        from algorithms.registry import build_algorithm_runner, get_algorithm_names

        self.assertIn("mra", get_algorithm_names())
        self.assertIn("ramcom", get_algorithm_names())

        environment = ChengduEnvironment(
            tasks=[],
            local_couriers=[],
            partner_couriers_by_platform={},
            station_set=[],
            travel_model=None,
            platform_base_prices={},
            platform_sharing_rates={},
            platform_qualities={},
        )

        def fake_runner(**kwargs):
            return {
                "TR": 1.0,
                "CR": 0.5,
                "BPT": 0.1,
                "delivered_parcels": 1,
                "accepted_assignments": 1,
            }

        for algorithm_name in ["mra", "ramcom"]:
            runner = build_algorithm_runner(algorithm_name, baseline_runner=fake_runner)
            summary = runner.run(environment=environment, output_dir=None)
            self.assertEqual(summary["algorithm"], algorithm_name)
            self.assertEqual(summary["metrics"]["TR"], 1.0)


if __name__ == "__main__":
    unittest.main()
