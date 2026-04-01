"""Tests for the unified root-runner strategy dispatch layer."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from capa import DistanceMatrixTravelModel
from env.chengdu import ChengduEnvironment
from tests.test_chengdu_runner import FakeLegacyCourier, FakeStation, FakeTask


class RunnerDispatchTests(unittest.TestCase):
    """Validate algorithm dispatch before the root CLI is added."""

    def test_capa_strategy_runs_against_unified_environment(self) -> None:
        """The CAPA strategy wrapper should run against the unified Chengdu environment."""
        from algorithms.registry import build_algorithm_runner

        travel = DistanceMatrixTravelModel(
            distances={
                ("L0", "T1"): 2.0,
                ("L0", "S"): 4.0,
                ("T1", "S"): 2.0,
                ("P0", "PS"): 4.0,
                ("P0", "T1"): 8.0,
                ("T1", "PS"): 6.0,
            },
            speed=1.0,
        )
        local_station = FakeStation(1, "S")
        partner_station = FakeStation(2, "PS")
        environment = ChengduEnvironment(
            tasks=[FakeTask("t1", "T1", 0, 30, 1.0, 10.0)],
            local_couriers=[FakeLegacyCourier(num=1, location="L0", station=local_station)],
            partner_couriers_by_platform={"P1": [FakeLegacyCourier(num=2, location="P0", station=partner_station)]},
            station_set=[local_station, partner_station],
            travel_model=travel,
            platform_base_prices={"P1": 1.0},
            platform_sharing_rates={"P1": 0.4},
            platform_qualities={"P1": 1.0},
            movement_callback=lambda local, partner, step, station_set: [
                courier.re_schedule.pop(0)
                for courier in [*local, *partner]
                if getattr(courier, "re_schedule", [])
            ],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            runner = build_algorithm_runner("capa", batch_size=60)
            result = runner.run(environment=environment, output_dir=Path(tmpdir))

        self.assertEqual(result["algorithm"], "capa")
        self.assertIn("metrics", result)
        self.assertIn("TR", result["metrics"])

    def test_all_baselines_share_same_environment_contract(self) -> None:
        """Greedy, BaseGTA, and ImpGTA should all dispatch through the same runner interface."""
        from algorithms.registry import build_algorithm_runner

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

        def fake_baseline_runner(**kwargs):
            return {
                "TR": 1.0,
                "CR": 0.5,
                "BPT": 0.1,
                "delivered_parcels": 1,
                "accepted_assignments": 1,
            }

        for name in ["greedy", "basegta", "impgta"]:
            runner = build_algorithm_runner(name, baseline_runner=fake_baseline_runner)
            result = runner.run(environment=environment, output_dir=None)
            self.assertEqual(result["algorithm"], name)
            self.assertEqual(result["metrics"]["TR"], 1.0)


if __name__ == "__main__":
    unittest.main()
