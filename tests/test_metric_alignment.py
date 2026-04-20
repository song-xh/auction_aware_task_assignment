"""Regression tests for unified baseline metric accounting."""

from __future__ import annotations

import py_compile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from baselines.greedy import run_greedy_baseline_environment
from baselines.gta import GTABid, run_basegta_baseline_environment, run_impgta_baseline_environment
from baselines.mra import run_mra_baseline_environment
from baselines.ramcom import run_ramcom_baseline_environment


class MetricAlignmentTest(unittest.TestCase):
    """Lock down the shared environment and metric-surface invariants."""

    def test_env_chengdu_compiles_cleanly(self) -> None:
        """`env/chengdu.py` should compile without merge-conflict markers."""

        source = Path(__file__).resolve().parents[1] / "env" / "chengdu.py"
        py_compile.compile(str(source), doraise=True)

    def test_basegta_uses_delivered_count_for_cr(self) -> None:
        """BaseGTA should derive delivered count from post-drain route state, not accepts."""

        task = SimpleNamespace(num="t1", fare=10.0, s_time=0.0, d_time=10.0, weight=1.0, l_node="p1")
        courier = SimpleNamespace(num=1, location="start", re_schedule=[], re_weight=0.0, max_weight=5.0)
        environment = SimpleNamespace(
            tasks=[task],
            local_couriers=[courier],
            partner_couriers_by_platform={},
            movement_callback=lambda *args, **kwargs: None,
            station_set=[],
            travel_model=SimpleNamespace(distance=lambda start, end: 0.0, travel_time=lambda start, end: 0.0),
            service_radius_km=None,
        )

        with (
            patch(
                "baselines.gta.select_available_courier_for_task",
                return_value=GTABid(platform_id="", courier=courier, dispatch_cost=1.0),
            ),
            patch("baselines.gta.drain_legacy_routes", return_value=1),
        ):
            result = run_basegta_baseline_environment(environment=environment)

        self.assertEqual(result["delivered_parcels"], 0)
        self.assertEqual(result["CR"], 0.0)

    def test_impgta_uses_delivered_count_for_cr(self) -> None:
        """ImpGTA should derive delivered count from post-drain route state, not accepts."""

        task = SimpleNamespace(num="t1", fare=10.0, s_time=0.0, d_time=10.0, weight=1.0, l_node="p1")
        courier = SimpleNamespace(num=1, location="start", re_schedule=[], re_weight=0.0, max_weight=5.0)
        environment = SimpleNamespace(
            tasks=[task],
            local_couriers=[courier],
            partner_couriers_by_platform={},
            movement_callback=lambda *args, **kwargs: None,
            station_set=[],
            travel_model=SimpleNamespace(distance=lambda start, end: 0.0, travel_time=lambda start, end: 0.0),
            service_radius_km=None,
        )

        with (
            patch(
                "baselines.gta.select_available_courier_for_task",
                return_value=GTABid(platform_id="", courier=courier, dispatch_cost=1.0),
            ),
            patch("baselines.gta.drain_legacy_routes", return_value=1),
        ):
            result = run_impgta_baseline_environment(environment=environment)

        self.assertEqual(result["delivered_parcels"], 0)
        self.assertEqual(result["CR"], 0.0)

    def test_basegta_cross_tr_uses_second_lowest_aim_payment(self) -> None:
        """BaseGTA should report cross revenue from AIM's critical payment."""

        task = SimpleNamespace(num="t1", fare=10.0, s_time=0.0, d_time=10.0, weight=1.0, l_node="p1")
        local_courier = SimpleNamespace(num=1, location="local", re_schedule=[], re_weight=0.0, max_weight=5.0)
        outer_one = SimpleNamespace(num=11, location="o1", re_schedule=[], re_weight=0.0, max_weight=5.0)
        outer_two = SimpleNamespace(num=12, location="o2", re_schedule=[], re_weight=0.0, max_weight=5.0)
        environment = SimpleNamespace(
            tasks=[task],
            local_couriers=[local_courier],
            partner_couriers_by_platform={"p1": [outer_one], "p2": [outer_two]},
            movement_callback=lambda *args, **kwargs: None,
            station_set=[],
            travel_model=SimpleNamespace(distance=lambda start, end: 0.0, travel_time=lambda start, end: 0.0),
            service_radius_km=None,
        )

        def fake_select(*, couriers, **kwargs):
            if couriers == [local_courier]:
                return None
            if couriers == [outer_one]:
                return GTABid(platform_id="", courier=outer_one, dispatch_cost=5.2)
            if couriers == [outer_two]:
                return GTABid(platform_id="", courier=outer_two, dispatch_cost=6.1)
            return None

        with (
            patch("baselines.gta.select_available_courier_for_task", side_effect=fake_select),
            patch("baselines.gta.drain_legacy_routes", return_value=1),
        ):
            result = run_basegta_baseline_environment(environment=environment)

        self.assertAlmostEqual(result["TR"], 10.0 - 6.1)

    def test_greedy_uses_delivered_count_for_cr(self) -> None:
        """Greedy should derive delivered count from post-drain route state, not accepts."""

        task = SimpleNamespace(num="t1", fare=10.0, s_time=0.0, d_time=10.0, weight=1.0, l_node="p1")
        courier = SimpleNamespace(num=1, location="start", re_schedule=[], re_weight=0.0, max_weight=5.0)
        environment = SimpleNamespace(
            tasks=[task],
            local_couriers=[courier],
            movement_callback=lambda *args, **kwargs: None,
            station_set=[],
            travel_model=SimpleNamespace(distance=lambda start, end: 0.0, travel_time=lambda start, end: 0.0),
            service_radius_km=None,
            geo_index=None,
            travel_speed_m_per_s=0.0,
        )

        with (
            patch("baselines.greedy.select_greedy_assignment", return_value=(courier, 0, 1.0)),
            patch("baselines.greedy.drain_legacy_routes", return_value=1),
        ):
            result = run_greedy_baseline_environment(environment=environment, batch_size=30)

        self.assertEqual(result["delivered_parcels"], 0)
        self.assertEqual(result["CR"], 0.0)

    def test_mra_uses_delivered_count_for_cr(self) -> None:
        """MRA should derive delivered count from post-drain route state, not accepts."""

        task = SimpleNamespace(num="t1", fare=10.0, s_time=0.0, d_time=10.0, weight=1.0, l_node="p1")
        courier = SimpleNamespace(num=1, location="start", re_schedule=[], re_weight=0.0, max_weight=5.0)
        environment = SimpleNamespace(
            tasks=[task],
            local_couriers=[courier],
            movement_callback=lambda *args, **kwargs: None,
            station_set=[],
            travel_model=SimpleNamespace(distance=lambda start, end: 0.0, travel_time=lambda start, end: 0.0),
            service_radius_km=None,
            geo_index=None,
            travel_speed_m_per_s=0.0,
        )

        with (
            patch("baselines.mra.group_legacy_tasks_by_batch", return_value=[[task]]),
            patch(
                "baselines.mra.build_legacy_feasible_insertions",
                return_value=[SimpleNamespace(courier=courier, insertion_index=0, distance_meters=1.0)],
            ),
            patch("baselines.mra.compute_mra_bid", return_value=1.0),
            patch("baselines.mra.drain_legacy_routes", return_value=1),
        ):
            result = run_mra_baseline_environment(environment=environment, batch_size=30)

        self.assertEqual(result["delivered_parcels"], 0)
        self.assertEqual(result["CR"], 0.0)

    def test_ramcom_uses_delivered_count_for_cr(self) -> None:
        """RamCOM should derive delivered count from post-drain route state, not accepts."""

        task = SimpleNamespace(num="t1", fare=20.0, s_time=0.0, d_time=10.0, weight=1.0, l_node="p1")
        courier = SimpleNamespace(num=1, location="start", re_schedule=[], re_weight=0.0, max_weight=5.0)
        environment = SimpleNamespace(
            tasks=[task],
            local_couriers=[courier],
            partner_couriers_by_platform={},
            movement_callback=lambda *args, **kwargs: None,
            station_set=[],
            travel_model=SimpleNamespace(distance=lambda start, end: 0.0, travel_time=lambda start, end: 0.0),
            service_radius_km=None,
            geo_index=None,
            travel_speed_m_per_s=0.0,
        )

        with (
            patch(
                "baselines.ramcom.build_legacy_feasible_insertions",
                return_value=[SimpleNamespace(courier=courier, insertion_index=0, distance_meters=1.0)],
            ),
            patch("baselines.ramcom.drain_legacy_routes", return_value=1),
        ):
            result = run_ramcom_baseline_environment(environment=environment)

        self.assertEqual(result["delivered_parcels"], 0)
        self.assertEqual(result["CR"], 0.0)


if __name__ == "__main__":
    unittest.main()
