"""Regression tests for unified baseline metric accounting."""

from __future__ import annotations

import py_compile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from capa.config import DEFAULT_CROSS_PLATFORM_SHARING_RATE_MU2
from capa.utility import DistanceMatrixTravelModel
from baselines.greedy import run_greedy_baseline_environment
from baselines.gta import GTABid, future_tasks_within_window, run_basegta_baseline_environment, run_impgta_baseline_environment
from baselines.mra import run_mra_baseline_environment
from baselines.ramcom import run_ramcom_baseline_environment
from env.chengdu import ChengduEnvironment, select_station_pick_tasks
from experiments.config import ExperimentConfig
from experiments.paper_chengdu import build_fixed_config_from_args, build_paper_runner_overrides_from_fixed_config
from experiments.seeding import build_environment_seed, clone_environment_from_seed
from runner import build_algorithm_kwargs


class MetricAlignmentTest(unittest.TestCase):
    """Lock down the shared environment and metric-surface invariants."""

    def test_env_chengdu_compiles_cleanly(self) -> None:
        """`env/chengdu.py` should compile without merge-conflict markers."""

        source = Path(__file__).resolve().parents[1] / "env" / "chengdu.py"
        py_compile.compile(str(source), doraise=True)

    def test_select_station_pick_tasks_samples_within_window(self) -> None:
        """Parcel selection should sample within the requested window rather than taking a time prefix."""

        station = SimpleNamespace(station_range=(0.0, 1.0, 0.0, 1.0), f_pick_task_set=[])
        tasks = [
            SimpleNamespace(num=f"t{i}", s_time=float(i), d_time=float(i + 100), l_lng=0.5, l_lat=0.5)
            for i in range(10)
        ]

        selected = select_station_pick_tasks(
            [station],
            tasks,
            num_parcels=3,
            window_start_seconds=2,
            window_end_seconds=7,
            sampling_seed=7,
        )

        self.assertEqual([task.num for task in selected], ["t3", "t4", "t5"])
        self.assertEqual([task.num for task in station.f_pick_task_set], ["t3", "t4", "t5"])

    def test_select_station_pick_tasks_rejects_window_underflow(self) -> None:
        """Parcel selection should fail clearly when the requested window has too few tasks."""

        station = SimpleNamespace(station_range=(0.0, 1.0, 0.0, 1.0), f_pick_task_set=[])
        tasks = [
            SimpleNamespace(num=f"t{i}", s_time=float(i), d_time=float(i + 100), l_lng=0.5, l_lat=0.5)
            for i in range(5)
        ]

        with self.assertRaisesRegex(ValueError, "fewer than the requested 4"):
            select_station_pick_tasks(
                [station],
                tasks,
                num_parcels=4,
                window_start_seconds=3,
                window_end_seconds=4,
                sampling_seed=1,
            )

    def test_experiment_config_carries_task_window_sampling(self) -> None:
        """Experiment configs should propagate task-window sampling into environment kwargs."""

        config = ExperimentConfig(
            data_dir=Path("Data"),
            task_window_start_seconds=100,
            task_window_end_seconds=200,
            task_sampling_seed=9,
        )

        environment_kwargs = config.as_environment_kwargs()

        self.assertEqual(environment_kwargs["task_window_start_seconds"], 100)
        self.assertEqual(environment_kwargs["task_window_end_seconds"], 200)
        self.assertEqual(environment_kwargs["task_sampling_seed"], 9)

    def test_build_fixed_config_from_args_carries_task_window_sampling(self) -> None:
        """Paper CLI translation should preserve task-window sampling fields."""

        args = SimpleNamespace(
            data_dir="Data",
            num_parcels=100,
            local_couriers=10,
            platforms=2,
            couriers_per_platform=5,
            courier_capacity=50.0,
            service_radius_km=1.0,
            batch_size=30,
            prediction_window_seconds=180,
            prediction_success_rate=0.6,
            prediction_sampling_seed=17,
            task_window_start_seconds=120,
            task_window_end_seconds=600,
            task_sampling_seed=13,
        )

        fixed_config = build_fixed_config_from_args(args)

        self.assertEqual(fixed_config["task_window_start_seconds"], 120)
        self.assertEqual(fixed_config["task_window_end_seconds"], 600)
        self.assertEqual(fixed_config["task_sampling_seed"], 13)
        self.assertEqual(fixed_config["prediction_window_seconds"], 180)
        self.assertEqual(fixed_config["prediction_success_rate"], 0.6)
        self.assertEqual(fixed_config["prediction_sampling_seed"], 17)

    def test_environment_seed_preserves_task_window_sampling(self) -> None:
        """Canonical Chengdu seeds should preserve task-window sampling metadata across clones."""

        environment = ChengduEnvironment(
            tasks=[],
            local_couriers=[],
            partner_couriers_by_platform={},
            station_set=[],
            travel_model=SimpleNamespace(),
            platform_base_prices={},
            platform_sharing_rates={},
            platform_qualities={},
            task_window_start_seconds=50,
            task_window_end_seconds=500,
            task_sampling_seed=21,
        )

        seed = build_environment_seed(environment)
        cloned = clone_environment_from_seed(seed)

        self.assertEqual(seed.task_window_start_seconds, 50)
        self.assertEqual(seed.task_window_end_seconds, 500)
        self.assertEqual(seed.task_sampling_seed, 21)
        self.assertEqual(cloned.task_window_start_seconds, 50)
        self.assertEqual(cloned.task_window_end_seconds, 500)
        self.assertEqual(cloned.task_sampling_seed, 21)

    def test_environment_seed_preserves_partner_own_task_streams(self) -> None:
        """Canonical Chengdu seeds should replay partner-platform own-task streams."""

        partner_task = SimpleNamespace(num="p-own-1", s_time=30.0, d_time=300.0, fare=50.0)
        environment = ChengduEnvironment(
            tasks=[],
            local_couriers=[],
            partner_couriers_by_platform={"P1": []},
            station_set=[],
            travel_model=SimpleNamespace(),
            platform_base_prices={"P1": 1.0},
            platform_sharing_rates={"P1": 0.5},
            platform_qualities={"P1": 1.0},
            partner_tasks_by_platform={"P1": [partner_task]},
        )

        seed = build_environment_seed(environment)
        cloned = clone_environment_from_seed(seed)

        self.assertEqual([task.num for task in seed.partner_tasks_by_platform["P1"]], ["p-own-1"])
        self.assertEqual([task.num for task in cloned.partner_tasks_by_platform["P1"]], ["p-own-1"])

    def test_impgta_prediction_success_rate_controls_future_window(self) -> None:
        """ImpGTA should preserve the full simplified future window when prediction success is 100%."""

        tasks = [
            SimpleNamespace(num=f"t{i}", s_time=float(i * 10), fare=float(i + 1))
            for i in range(1, 6)
        ]

        predicted = future_tasks_within_window(
            tasks,
            now=0,
            window_seconds=60,
            prediction_success_rate=1.0,
            prediction_sampling_seed=11,
        )

        self.assertEqual([task.num for task in predicted], ["t1", "t2", "t3", "t4", "t5"])

    def test_impgta_zero_success_rate_removes_future_signal(self) -> None:
        """ImpGTA should see no predicted future tasks when prediction success is zero."""

        tasks = [
            SimpleNamespace(num=f"t{i}", s_time=float(i * 10), fare=float(i + 1))
            for i in range(1, 6)
        ]

        predicted = future_tasks_within_window(
            tasks,
            now=0,
            window_seconds=60,
            prediction_success_rate=0.0,
            prediction_sampling_seed=11,
        )

        self.assertEqual(predicted, [])

    def test_impgta_prediction_success_rate_uses_deterministic_subset(self) -> None:
        """ImpGTA should down-sample the simplified future window deterministically under a fixed seed."""

        tasks = [
            SimpleNamespace(num=f"t{i}", s_time=float(i * 10), fare=float(i + 1))
            for i in range(1, 6)
        ]

        predicted = future_tasks_within_window(
            tasks,
            now=0,
            window_seconds=60,
            prediction_success_rate=0.5,
            prediction_sampling_seed=11,
        )

        self.assertEqual([task.num for task in predicted], ["t3", "t4", "t5"])

    def test_impgta_outer_prediction_success_rate_changes_partner_bid_decision(self) -> None:
        """ImpGTA outer bidding should use partner own-task predictions, not an empty future window."""

        task = SimpleNamespace(num="t1", fare=20.0, s_time=0.0, d_time=300.0, weight=1.0, l_node="p1")
        future_tasks = [
            SimpleNamespace(num="p-f1", fare=100.0, s_time=10.0, d_time=400.0, weight=1.0, l_node="p2"),
            SimpleNamespace(num="p-f2", fare=100.0, s_time=20.0, d_time=500.0, weight=1.0, l_node="p3"),
        ]

        def build_environment() -> SimpleNamespace:
            local_courier = SimpleNamespace(num=1, location="local", re_schedule=[], re_weight=0.0, max_weight=5.0)
            partner_courier = SimpleNamespace(num=11, location="outer", re_schedule=[], re_weight=0.0, max_weight=5.0)
            return SimpleNamespace(
                tasks=[task],
                local_couriers=[local_courier],
                partner_couriers_by_platform={"P1": [partner_courier]},
                partner_tasks_by_platform={"P1": list(future_tasks)},
                movement_callback=lambda *args, **kwargs: None,
                station_set=[],
                travel_model=SimpleNamespace(distance=lambda start, end: 0.0, travel_time=lambda start, end: 0.0),
                service_radius_km=None,
            )

        def fake_select(*, couriers, **kwargs):
            if getattr(couriers[0], "num") == 1:
                return None
            return GTABid(platform_id="", courier=couriers[0], dispatch_cost=1.0)

        with (
            patch("baselines.gta.select_available_courier_for_task", side_effect=fake_select),
            patch("baselines.gta.drain_legacy_routes", return_value=1),
        ):
            zero_success = run_impgta_baseline_environment(
                environment=build_environment(),
                prediction_window_seconds=100,
                prediction_success_rate=0.0,
            )
            full_success = run_impgta_baseline_environment(
                environment=build_environment(),
                prediction_window_seconds=100,
                prediction_success_rate=1.0,
            )

        self.assertEqual(zero_success["accepted_assignments"], 1)
        self.assertEqual(full_success["accepted_assignments"], 0)

    def test_runner_builds_impgta_prediction_success_kwargs(self) -> None:
        """Unified runner kwargs should expose ImpGTA prediction-success controls."""

        args = SimpleNamespace(
            algorithm="impgta",
            prediction_window_seconds=180,
            prediction_success_rate=0.6,
            prediction_sampling_seed=17,
        )

        kwargs = build_algorithm_kwargs(args)

        self.assertEqual(kwargs["prediction_window_seconds"], 180)
        self.assertEqual(kwargs["prediction_success_rate"], 0.6)
        self.assertEqual(kwargs["prediction_sampling_seed"], 17)

    def test_paper_runner_overrides_include_impgta_prediction_controls(self) -> None:
        """Paper point/split execution should forward ImpGTA prediction controls into the point runner."""

        overrides = build_paper_runner_overrides_from_fixed_config(
            {
                "prediction_window_seconds": 240,
                "prediction_success_rate": 0.55,
                "prediction_sampling_seed": 19,
            }
        )

        self.assertEqual(overrides["impgta"]["prediction_window_seconds"], 240)
        self.assertEqual(overrides["impgta"]["prediction_success_rate"], 0.55)
        self.assertEqual(overrides["impgta"]["prediction_sampling_seed"], 19)

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

    def test_basegta_local_tr_uses_capa_local_revenue(self) -> None:
        """BaseGTA local revenue should equal fare minus the local courier payment."""

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
            patch("baselines.gta.drain_legacy_routes", return_value=0),
        ):
            result = run_basegta_baseline_environment(environment=environment, local_payment_ratio=0.3)

        self.assertAlmostEqual(result["TR"], 7.0)

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

    def test_impgta_local_tr_uses_capa_local_revenue(self) -> None:
        """ImpGTA local revenue should equal fare minus the local courier payment."""

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
            patch("baselines.gta.drain_legacy_routes", return_value=0),
        ):
            result = run_impgta_baseline_environment(environment=environment, local_payment_ratio=0.3)

        self.assertAlmostEqual(result["TR"], 7.0)

    def test_impgta_cross_tr_uses_platform_payment_with_partner_sharing(self) -> None:
        """ImpGTA should also deduct partner-platform sharing payment on cross completions."""

        task = SimpleNamespace(num="t1", fare=20.0, s_time=0.0, d_time=10.0, weight=1.0, l_node="p1")
        local_courier = SimpleNamespace(num=1, location="local", re_schedule=[], re_weight=0.0, max_weight=5.0)
        outer_one = SimpleNamespace(num=11, location="o1", re_schedule=[], re_weight=0.0, max_weight=5.0)
        outer_two = SimpleNamespace(num=12, location="o2", re_schedule=[], re_weight=0.0, max_weight=5.0)
        environment = SimpleNamespace(
            tasks=[task],
            local_couriers=[local_courier],
            partner_couriers_by_platform={"p1": [outer_one], "p2": [outer_two]},
            partner_tasks_by_platform={"p1": [], "p2": []},
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
            result = run_impgta_baseline_environment(environment=environment)

        self.assertAlmostEqual(result["TR"], 20.0 - (6.1 + DEFAULT_CROSS_PLATFORM_SHARING_RATE_MU2 * 20.0))

    def test_basegta_cross_tr_uses_platform_payment_with_partner_sharing(self) -> None:
        """BaseGTA should report cross revenue after deducting partner-platform sharing payment."""

        task = SimpleNamespace(num="t1", fare=20.0, s_time=0.0, d_time=10.0, weight=1.0, l_node="p1")
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

        self.assertAlmostEqual(result["TR"], 20.0 - (6.1 + DEFAULT_CROSS_PLATFORM_SHARING_RATE_MU2 * 20.0))

    def test_select_available_courier_uses_insertion_increment_dispatch_cost(self) -> None:
        """GTA dispatch cost should use incremental insertion distance under the CPUL route model."""

        from baselines.gta import select_available_courier_for_task

        courier = SimpleNamespace(
            num=1,
            location="S",
            re_schedule=[
                SimpleNamespace(l_node="A", reach_time=5.0),
                SimpleNamespace(l_node="B", reach_time=10.0),
            ],
            re_weight=0.0,
            max_weight=5.0,
        )
        task = SimpleNamespace(num="t1", l_node="X", d_time=200.0, weight=1.0)
        travel_model = DistanceMatrixTravelModel(
            distances={
                ("S", "A"): 10.0,
                ("A", "B"): 10.0,
                ("S", "X"): 6.0,
                ("X", "A"): 6.0,
                ("A", "X"): 7.0,
                ("X", "B"): 7.0,
                ("B", "X"): 50.0,
            },
            speed=1.0,
        )

        bid = select_available_courier_for_task(
            task=task,
            couriers=[courier],
            travel_model=travel_model,
            now=0,
            unit_price_per_km=3.0,
        )

        self.assertIsNotNone(bid)
        self.assertAlmostEqual(bid.dispatch_cost, (2.0 / 1000.0) * 3.0)
        self.assertEqual(getattr(bid, "insertion_index", None), 0)

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
