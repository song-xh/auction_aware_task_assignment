"""Regression tests for unified baseline metric accounting."""

from __future__ import annotations

import py_compile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from capa.config import DEFAULT_CROSS_PLATFORM_SHARING_RATE_MU2
from capa.metrics import compute_batch_processing_time
from capa.models import BatchReport, BatchTimingBreakdown
from capa.utility import DistanceMatrixTravelModel, compute_local_platform_revenue_for_local_completion
from baselines.greedy import run_greedy_baseline_environment
from baselines.gta import (
    GTABid,
    estimate_impgta_outer_task_value,
    future_tasks_within_window,
    run_basegta_baseline_environment,
    run_impgta_baseline_environment,
    settle_aim_auction,
    should_bid_outer_platform_impgta,
    should_dispatch_inner_task_impgta,
)
from baselines.mra import run_mra_baseline_environment
from baselines.ramcom import choose_outer_payment_by_expected_revenue, run_ramcom_baseline_environment, worker_acceptance_probability
from algorithms.ramcom_runner import build_ramcom_runner
from env.chengdu import ChengduEnvironment, select_station_pick_tasks
from experiments.config import ExperimentConfig
from experiments.paper_chengdu import build_fixed_config_from_args, build_paper_runner_overrides_from_fixed_config
from experiments.seeding import build_environment_seed, clone_environment_from_seed
from runner import build_algorithm_kwargs


def _complete_routes(
    local_couriers: list[SimpleNamespace],
    partner_couriers: list[SimpleNamespace],
    *_args: object,
    **_kwargs: object,
) -> None:
    """Simulate one movement step by completing every queued legacy route."""

    for courier in [*local_couriers, *partner_couriers]:
        if getattr(courier, "re_schedule", []):
            courier.location = courier.re_schedule[-1].l_node
        courier.re_schedule.clear()
        courier.re_weight = 0.0


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

    def test_capa_bpt_is_mean_assignment_time_per_batch(self) -> None:
        """CAPA BPT should be the mean assignment-decision time per matching batch."""

        reports = [
            BatchReport(
                batch_index=1,
                batch_time=30,
                input_parcels=[],
                local_assignments=[],
                cross_assignments=[],
                unresolved_parcels=[],
                processing_time_seconds=10.0,
                timing=BatchTimingBreakdown(decision_time_seconds=2.0),
            ),
            BatchReport(
                batch_index=2,
                batch_time=60,
                input_parcels=[],
                local_assignments=[],
                cross_assignments=[],
                unresolved_parcels=[],
                processing_time_seconds=20.0,
                timing=BatchTimingBreakdown(decision_time_seconds=4.0),
            ),
        ]

        self.assertEqual(compute_batch_processing_time(reports), 3.0)

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

    def test_impgta_available_supply_counts_capacity_slots(self) -> None:
        """ImpGTA's CPUL adaptation should compare predicted tasks to residual courier capacity."""

        from baselines.gta import count_available_capacity_slots

        couriers = [
            SimpleNamespace(max_weight=50.0, re_weight=10.0, re_schedule=[], location="a"),
            SimpleNamespace(max_weight=25.0, re_weight=20.0, re_schedule=[], location="b"),
        ]

        self.assertEqual(count_available_capacity_slots(couriers, now=0), 45)

    def test_impgta_inner_condition_uses_capacity_not_raw_worker_count(self) -> None:
        """A high-capacity courier should satisfy ImpGTA supply even when one worker faces many future tasks."""

        current_task = SimpleNamespace(num="t0", fare=10.0, s_time=0.0, d_time=300.0, weight=1.0, l_node="p0", reach_time=0.0)
        future_tasks = [
            SimpleNamespace(num=f"t{i}", fare=100.0, s_time=float(i * 10), d_time=400.0, weight=1.0, l_node=f"p{i}", reach_time=float(i * 10))
            for i in range(1, 4)
        ]
        courier = SimpleNamespace(num=1, location="start", re_schedule=[], re_weight=0.0, max_weight=5.0)
        environment = SimpleNamespace(
            tasks=[current_task, *future_tasks],
            local_couriers=[courier],
            partner_couriers_by_platform={},
            partner_tasks_by_platform={},
            movement_callback=_complete_routes,
            station_set=[],
            travel_model=SimpleNamespace(distance=lambda start, end: 0.0, travel_time=lambda start, end: 0.0),
            service_radius_km=None,
        )

        with (
            patch(
                "baselines.gta.select_available_courier_for_task",
                return_value=GTABid(platform_id="", courier=courier, dispatch_cost=1.0, insertion_index=0),
            ),
            patch("baselines.gta.drain_legacy_routes", return_value=1),
        ):
            result = run_impgta_baseline_environment(
                environment=environment,
                prediction_window_seconds=100,
                prediction_success_rate=1.0,
            )

        self.assertEqual(result["accepted_assignments"], 4)
        self.assertEqual(result["local_assignment_count"], 4)

    def test_impgta_inner_condition_compares_capacity_to_future_weight(self) -> None:
        """ImpGTA local gating should compare residual capacity against future parcel weight."""

        current_task = SimpleNamespace(num="t0", fare=10.0, weight=1.0)
        future_tasks = [
            SimpleNamespace(num="f1", fare=100.0, weight=3.0),
            SimpleNamespace(num="f2", fare=100.0, weight=3.0),
            SimpleNamespace(num="f3", fare=100.0, weight=3.0),
        ]

        self.assertFalse(
            should_dispatch_inner_task_impgta(
                task=current_task,
                available_capacity_weight=5.0,
                future_tasks=future_tasks,
            )
        )

    def test_impgta_outer_prediction_success_rate_changes_partner_bid_decision(self) -> None:
        """ImpGTA outer bidding should use partner own-task predictions, not an empty future window."""

        task = SimpleNamespace(num="t1", fare=20.0, s_time=0.0, d_time=300.0, weight=1.0, l_node="p1")
        future_tasks = [
            SimpleNamespace(num="p-f1", fare=100.0, s_time=10.0, d_time=400.0, weight=1.0, l_node="p2"),
            SimpleNamespace(num="p-f2", fare=100.0, s_time=20.0, d_time=500.0, weight=1.0, l_node="p3"),
        ]

        def build_environment() -> SimpleNamespace:
            partner_station = SimpleNamespace(l_node="depot")
            local_courier = SimpleNamespace(num=1, location="local", re_schedule=[], re_weight=0.0, max_weight=5.0)
            partner_courier = SimpleNamespace(
                num=11,
                location="outer",
                re_schedule=[],
                re_weight=0.0,
                max_weight=1.0,
                station=partner_station,
                station_num=1,
                w=0.5,
                c=0.5,
                service_score=0.8,
            )
            return SimpleNamespace(
                tasks=[task],
                local_couriers=[local_courier],
                partner_couriers_by_platform={"P1": [partner_courier]},
                partner_tasks_by_platform={"P1": list(future_tasks)},
                movement_callback=_complete_routes,
                station_set=[],
                travel_model=SimpleNamespace(distance=lambda start, end: 0.0, travel_time=lambda start, end: 0.0),
                service_radius_km=None,
                platform_base_prices={"P1": 1.0},
                platform_sharing_rates={"P1": 0.5},
                platform_qualities={"P1": 1.0},
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

    def test_impgta_outer_condition_uses_estimated_cross_reward_not_dispatch_cost(self) -> None:
        """Outer ImpGTA should compare predicted demand with expected cooperative payment, not cost only."""

        task = SimpleNamespace(num="t1", fare=20.0, s_time=0.0, d_time=300.0, weight=1.0, l_node="p1")
        partner_future_tasks = [
            SimpleNamespace(num="p-f1", fare=10.0, s_time=10.0, d_time=400.0, weight=1.0, l_node="p2"),
            SimpleNamespace(num="p-f2", fare=10.0, s_time=20.0, d_time=500.0, weight=1.0, l_node="p3"),
        ]
        local_courier = SimpleNamespace(num=1, location="local", re_schedule=[], re_weight=0.0, max_weight=0.0)
        outer = SimpleNamespace(
            num=11,
            location="outer",
            re_schedule=[],
            re_weight=0.0,
            max_weight=1.0,
            station=SimpleNamespace(l_node="depot"),
            station_num=1,
            w=0.5,
            c=0.5,
            service_score=0.8,
        )
        environment = SimpleNamespace(
            tasks=[task],
            local_couriers=[local_courier],
            partner_couriers_by_platform={"P1": [outer]},
            partner_tasks_by_platform={"P1": partner_future_tasks},
            movement_callback=_complete_routes,
            station_set=[],
            travel_model=SimpleNamespace(distance=lambda start, end: 0.0, travel_time=lambda start, end: 0.0),
            service_radius_km=None,
            platform_base_prices={"P1": 1.0},
            platform_sharing_rates={"P1": 0.5},
            platform_qualities={"P1": 1.0},
        )

        def fake_select(*, couriers, **kwargs):
            if couriers == [local_courier]:
                return None
            return GTABid(platform_id="", courier=outer, dispatch_cost=1.0, insertion_index=0)

        with (
            patch("baselines.gta.select_available_courier_for_task", side_effect=fake_select),
            patch("baselines.gta.drain_legacy_routes", return_value=1),
        ):
            result = run_impgta_baseline_environment(
                environment=environment,
                prediction_window_seconds=100,
                prediction_success_rate=1.0,
            )

        self.assertEqual(result["accepted_assignments"], 1)
        self.assertEqual(result["cross_assignment_count"], 1)

    def test_impgta_outer_condition_compares_net_revenue_scales(self) -> None:
        """Outer ImpGTA should compare current and future opportunities as platform net revenue."""

        task = SimpleNamespace(num="t1", fare=20.0, s_time=0.0, d_time=300.0, weight=1.0, l_node="p1")
        future_tasks = [
            SimpleNamespace(num="p-f1", fare=11.0, s_time=10.0),
            SimpleNamespace(num="p-f2", fare=12.0, s_time=20.0),
        ]

        current_revenue = estimate_impgta_outer_task_value(
            task=task,
            dispatch_cost=1.0,
            cross_platform_sharing_rate_mu2=0.5,
        )

        self.assertEqual(current_revenue, 19.0)
        future_revenue = sum(
            compute_local_platform_revenue_for_local_completion(float(task.fare), local_payment_ratio=0.2)
            for task in future_tasks
        ) / len(future_tasks)
        self.assertEqual(future_revenue, 9.2)
        self.assertTrue(
            should_bid_outer_platform_impgta(
                current_task_value=current_revenue,
                available_capacity_weight=0,
                future_tasks=future_tasks,
            )
        )

    def test_impgta_cross_payment_matches_aim_critical_payment(self) -> None:
        """ImpGTA cross completions should settle with AIM critical payment."""

        task = SimpleNamespace(num="t1", fare=20.0, s_time=0.0, d_time=300.0, weight=1.0, l_node="X")
        local_courier = SimpleNamespace(num=1, location="L", re_schedule=[], re_weight=0.0, max_weight=0.0)
        station_one = SimpleNamespace(l_node="DA")
        station_two = SimpleNamespace(l_node="DB")
        outer_one = SimpleNamespace(
            num=11,
            location="A",
            re_schedule=[],
            re_weight=0.0,
            max_weight=5.0,
            station=station_one,
            station_num=1,
            w=0.5,
            c=0.5,
            service_score=0.8,
        )
        outer_two = SimpleNamespace(
            num=12,
            location="B",
            re_schedule=[],
            re_weight=0.0,
            max_weight=5.0,
            station=station_two,
            station_num=2,
            w=0.5,
            c=0.5,
            service_score=0.8,
        )
        travel_model = DistanceMatrixTravelModel(
            distances={
                ("A", "X"): 1000.0,
                ("X", "DA"): 1000.0,
                ("A", "DA"): 1500.0,
                ("B", "X"): 1000.0,
                ("X", "DB"): 1000.0,
                ("B", "DB"): 1500.0,
            },
            speed=1000.0,
        )
        environment = SimpleNamespace(
            tasks=[task],
            local_couriers=[local_courier],
            partner_couriers_by_platform={"P1": [outer_one], "P2": [outer_two]},
            partner_tasks_by_platform={"P1": [], "P2": []},
            movement_callback=_complete_routes,
            station_set=[],
            travel_model=travel_model,
            service_radius_km=None,
            platform_base_prices={},
            platform_sharing_rates={},
            platform_qualities={},
        )
        expected = settle_aim_auction(
            task,
            [
                GTABid(platform_id="P1", courier=outer_one, dispatch_cost=2.0, insertion_index=0),
                GTABid(platform_id="P2", courier=outer_two, dispatch_cost=2.0, insertion_index=0),
            ],
        )

        with patch("baselines.gta.drain_legacy_routes", return_value=1):
            result = run_impgta_baseline_environment(environment=environment, prediction_success_rate=0.0)

        self.assertIsNotNone(expected)
        self.assertAlmostEqual(result["TR"], float(task.fare) - expected.payment)

    def test_impgta_cross_assignment_uses_aim(self) -> None:
        """ImpGTA and BaseGTA should both settle cross assignments through AIM."""

        task = SimpleNamespace(num="t1", fare=20.0, s_time=0.0, d_time=300.0, weight=1.0, l_node="X")
        local_courier = SimpleNamespace(num=1, location="L", re_schedule=[], re_weight=0.0, max_weight=0.0)
        station = SimpleNamespace(l_node="D")
        outer = SimpleNamespace(
            num=11,
            location="A",
            re_schedule=[],
            re_weight=0.0,
            max_weight=5.0,
            station=station,
            station_num=1,
            w=0.5,
            c=0.5,
            service_score=0.8,
        )
        travel_model = DistanceMatrixTravelModel(
            distances={
                ("A", "X"): 1000.0,
                ("X", "D"): 1000.0,
                ("A", "D"): 1500.0,
            },
            speed=1000.0,
        )

        def build_environment() -> SimpleNamespace:
            fresh_local = SimpleNamespace(num=1, location="L", re_schedule=[], re_weight=0.0, max_weight=0.0)
            fresh_outer = SimpleNamespace(
                num=11,
                location="A",
                re_schedule=[],
                re_weight=0.0,
                max_weight=5.0,
                station=station,
                station_num=1,
                w=0.5,
                c=0.5,
                service_score=0.8,
            )
            return SimpleNamespace(
                tasks=[task],
                local_couriers=[fresh_local],
                partner_couriers_by_platform={"P1": [fresh_outer]},
                partner_tasks_by_platform={"P1": []},
                movement_callback=_complete_routes,
                station_set=[],
                travel_model=travel_model,
                service_radius_km=None,
                platform_base_prices={"P1": 1.0},
                platform_sharing_rates={"P1": 0.5},
                platform_qualities={"P1": 1.0},
            )

        with (
            patch("baselines.gta.settle_aim_auction", wraps=settle_aim_auction) as aim_spy,
            patch("baselines.gta.drain_legacy_routes", return_value=1),
        ):
            run_basegta_baseline_environment(environment=build_environment())
        self.assertGreater(aim_spy.call_count, 0)

        with (
            patch("baselines.gta.settle_aim_auction", wraps=settle_aim_auction) as aim_spy,
            patch("baselines.gta.drain_legacy_routes", return_value=1),
        ):
            run_impgta_baseline_environment(environment=build_environment(), prediction_success_rate=0.0)
        self.assertGreater(aim_spy.call_count, 0)

    def test_impgta_bpt_excludes_aim_routing_delay(self) -> None:
        """ImpGTA BPT should exclude routing delay even when cross settlement uses AIM."""

        class SlowTravelModel:
            """Travel model that records an artificial delay on every distance query."""

            speed = 1000.0

            def __init__(self) -> None:
                """Initialize deterministic distances and delay accounting."""

                self.delay_seconds = 0.002
                self.routing_delay_seconds = 0.0

            def distance(self, start, end) -> float:
                """Return a deterministic distance while simulating routing latency."""

                self.routing_delay_seconds += self.delay_seconds
                time.sleep(self.delay_seconds)
                if start == end:
                    return 0.0
                if {start, end} == {"A", "X"}:
                    return 1000.0
                if {start, end} == {"X", "D"}:
                    return 1000.0
                if {start, end} == {"A", "D"}:
                    return 1500.0
                raise KeyError((start, end))

            def travel_time(self, start, end) -> float:
                """Return travel time derived from the delayed distance query."""

                return self.distance(start, end) / self.speed

        task = SimpleNamespace(num="t1", fare=20.0, s_time=0.0, d_time=300.0, weight=1.0, l_node="X")
        local_courier = SimpleNamespace(num=1, location="L", re_schedule=[], re_weight=0.0, max_weight=0.0)
        outer = SimpleNamespace(
            num=11,
            location="A",
            re_schedule=[],
            re_weight=0.0,
            max_weight=5.0,
            station=SimpleNamespace(l_node="D"),
            station_num=1,
            w=0.5,
            c=0.5,
            service_score=0.8,
        )
        travel_model = SlowTravelModel()
        environment = SimpleNamespace(
            tasks=[task],
            local_couriers=[local_courier],
            partner_couriers_by_platform={"P1": [outer]},
            partner_tasks_by_platform={"P1": []},
            movement_callback=_complete_routes,
            station_set=[],
            travel_model=travel_model,
            service_radius_km=None,
            platform_base_prices={"P1": 1.0},
            platform_sharing_rates={"P1": 0.5},
            platform_qualities={"P1": 1.0},
        )

        with patch("baselines.gta.drain_legacy_routes", return_value=1):
            result = run_impgta_baseline_environment(environment=environment, prediction_success_rate=0.0)

        self.assertGreater(travel_model.routing_delay_seconds, 0.0)
        self.assertGreaterEqual(result["BPT"], 0.0)
        self.assertLess(result["BPT"], travel_model.routing_delay_seconds)

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

    def test_paper_runner_overrides_include_rl_capa_infer_checkpoint_controls(self) -> None:
        """Paper point/split execution should forward RL-CAPA inference checkpoint controls."""

        overrides = build_paper_runner_overrides_from_fixed_config(
            {
                "prediction_window_seconds": 180,
                "prediction_success_rate": 0.6,
                "prediction_sampling_seed": 17,
                "rl_future_feature_window_seconds": 420,
                "rl_checkpoint_dir": "outputs/plots/rl_capa_ablation_v2_500/rl-capa/checkpoints",
            }
        )

        self.assertEqual(overrides["rl-capa-infer"]["future_feature_window_seconds"], 420)
        self.assertEqual(
            overrides["rl-capa-infer"]["checkpoint_dir"],
            "outputs/plots/rl_capa_ablation_v2_500/rl-capa/checkpoints",
        )

    def test_basegta_uses_delivered_count_for_cr(self) -> None:
        """BaseGTA should derive delivered count from post-drain route state, not accepts."""

        task = SimpleNamespace(num="t1", fare=10.0, s_time=0.0, d_time=10.0, weight=1.0, l_node="p1")
        courier = SimpleNamespace(num=1, location="start", re_schedule=[], re_weight=0.0, max_weight=5.0)
        environment = SimpleNamespace(
            tasks=[task],
            local_couriers=[courier],
            partner_couriers_by_platform={},
            movement_callback=_complete_routes,
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

        task = SimpleNamespace(num="t1", fare=10.0, s_time=0.0, d_time=300.0, weight=1.0, l_node="p1")
        courier = SimpleNamespace(num=1, location="start", re_schedule=[], re_weight=0.0, max_weight=5.0)
        environment = SimpleNamespace(
            tasks=[task],
            local_couriers=[courier],
            partner_couriers_by_platform={},
            movement_callback=_complete_routes,
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

    def test_basegta_bpt_is_mean_assignment_time_per_task(self) -> None:
        """BaseGTA BPT should report mean assignment-decision time per task epoch."""

        tasks = [
            SimpleNamespace(num="t1", fare=10.0, s_time=0.0, d_time=10.0, weight=1.0, l_node="p1"),
            SimpleNamespace(num="t2", fare=10.0, s_time=0.0, d_time=10.0, weight=1.0, l_node="p2"),
        ]
        courier = SimpleNamespace(num=1, location="start", re_schedule=[], re_weight=0.0, max_weight=5.0)
        environment = SimpleNamespace(
            tasks=tasks,
            local_couriers=[courier],
            partner_couriers_by_platform={},
            movement_callback=_complete_routes,
            station_set=[],
            travel_model=SimpleNamespace(distance=lambda start, end: 0.0, travel_time=lambda start, end: 0.0),
            service_radius_km=None,
        )

        with (
            patch(
                "baselines.gta.select_available_courier_for_task",
                return_value=GTABid(platform_id="", courier=courier, dispatch_cost=1.0),
            ),
            patch("baselines.gta.drain_legacy_routes"),
            patch("baselines.gta.perf_counter", side_effect=[0.0, 2.0, 3.0, 7.0]),
        ):
            result = run_basegta_baseline_environment(environment=environment)

        self.assertEqual(result["BPT"], 3.0)

    def test_impgta_uses_delivered_count_for_cr(self) -> None:
        """ImpGTA should derive delivered count from post-drain route state, not accepts."""

        task = SimpleNamespace(num="t1", fare=10.0, s_time=0.0, d_time=10.0, weight=1.0, l_node="p1")
        courier = SimpleNamespace(num=1, location="start", re_schedule=[], re_weight=0.0, max_weight=5.0)
        environment = SimpleNamespace(
            tasks=[task],
            local_couriers=[courier],
            partner_couriers_by_platform={},
            movement_callback=_complete_routes,
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

        task = SimpleNamespace(num="t1", fare=10.0, s_time=0.0, d_time=300.0, weight=1.0, l_node="p1")
        courier = SimpleNamespace(num=1, location="start", re_schedule=[], re_weight=0.0, max_weight=5.0)
        environment = SimpleNamespace(
            tasks=[task],
            local_couriers=[courier],
            partner_couriers_by_platform={},
            movement_callback=_complete_routes,
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

    def test_impgta_cross_tr_uses_aim_platform_payment_with_partner_sharing(self) -> None:
        """ImpGTA should deduct AIM platform payment when reporting CAPA-aligned cross TR."""

        task = SimpleNamespace(num="t1", fare=20.0, s_time=0.0, d_time=300.0, weight=1.0, l_node="p1")
        local_courier = SimpleNamespace(num=1, location="local", re_schedule=[], re_weight=0.0, max_weight=5.0)
        outer_one = SimpleNamespace(
            num=11,
            location="o1",
            re_schedule=[],
            re_weight=0.0,
            max_weight=5.0,
            station=SimpleNamespace(l_node="d1"),
            station_num=1,
            w=0.5,
            c=0.5,
            service_score=0.8,
        )
        outer_two = SimpleNamespace(
            num=12,
            location="o2",
            re_schedule=[],
            re_weight=0.0,
            max_weight=5.0,
            station=SimpleNamespace(l_node="d2"),
            station_num=2,
            w=0.5,
            c=0.5,
            service_score=0.8,
        )
        travel_model = SimpleNamespace(distance=lambda start, end: 0.0, travel_time=lambda start, end: 0.0)
        environment = SimpleNamespace(
            tasks=[task],
            local_couriers=[local_courier],
            partner_couriers_by_platform={"p1": [outer_one], "p2": [outer_two]},
            partner_tasks_by_platform={"p1": [], "p2": []},
            movement_callback=_complete_routes,
            station_set=[],
            travel_model=travel_model,
            service_radius_km=None,
            platform_base_prices={},
            platform_sharing_rates={},
            platform_qualities={},
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

        expected = settle_aim_auction(
            task,
            [
                GTABid(platform_id="p1", courier=outer_one, dispatch_cost=5.2),
                GTABid(platform_id="p2", courier=outer_two, dispatch_cost=6.1),
            ],
        )
        self.assertIsNotNone(expected)
        self.assertAlmostEqual(result["TR"], float(task.fare) - expected.payment)

    def test_basegta_cross_tr_uses_platform_payment_with_partner_sharing(self) -> None:
        """BaseGTA should report cross revenue after deducting partner-platform sharing payment."""

        task = SimpleNamespace(num="t1", fare=20.0, s_time=0.0, d_time=300.0, weight=1.0, l_node="p1")
        local_courier = SimpleNamespace(num=1, location="local", re_schedule=[], re_weight=0.0, max_weight=5.0)
        outer_one = SimpleNamespace(num=11, location="o1", re_schedule=[], re_weight=0.0, max_weight=5.0)
        outer_two = SimpleNamespace(num=12, location="o2", re_schedule=[], re_weight=0.0, max_weight=5.0)
        environment = SimpleNamespace(
            tasks=[task],
            local_couriers=[local_courier],
            partner_couriers_by_platform={"p1": [outer_one], "p2": [outer_two]},
            movement_callback=_complete_routes,
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

        task = SimpleNamespace(num="t1", fare=10.0, s_time=0.0, d_time=0.0, weight=1.0, l_node="p1")
        courier = SimpleNamespace(num=1, location="start", re_schedule=[], re_weight=0.0, max_weight=5.0)
        environment = SimpleNamespace(
            tasks=[task],
            local_couriers=[courier],
            movement_callback=_complete_routes,
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

    def test_greedy_bpt_is_mean_assignment_time_per_task(self) -> None:
        """Greedy BPT should report mean assignment-decision time per task epoch."""

        tasks = [
            SimpleNamespace(num="t1", fare=10.0, s_time=0.0, d_time=10.0, weight=1.0, l_node="p1"),
            SimpleNamespace(num="t2", fare=10.0, s_time=0.0, d_time=10.0, weight=1.0, l_node="p2"),
        ]
        courier = SimpleNamespace(num=1, location="start", re_schedule=[], re_weight=0.0, max_weight=5.0)
        environment = SimpleNamespace(
            tasks=tasks,
            local_couriers=[courier],
            movement_callback=_complete_routes,
            station_set=[],
            travel_model=SimpleNamespace(distance=lambda start, end: 0.0, travel_time=lambda start, end: 0.0),
            service_radius_km=None,
        )

        with (
            patch("baselines.greedy.select_greedy_assignment", return_value=(courier, 0, 1.0)),
            patch("baselines.greedy.drain_legacy_routes"),
            patch("baselines.greedy.perf_counter", side_effect=[0.0, 2.0, 3.0, 7.0]),
        ):
            result = run_greedy_baseline_environment(environment=environment, batch_size=30)

        self.assertEqual(result["BPT"], 3.0)

    def test_mra_uses_delivered_count_for_cr(self) -> None:
        """MRA should derive delivered count from post-drain route state, not accepts."""

        task = SimpleNamespace(num="t1", fare=10.0, s_time=0.0, d_time=10.0, weight=1.0, l_node="p1")
        courier = SimpleNamespace(num=1, location="start", re_schedule=[], re_weight=0.0, max_weight=5.0)
        environment = SimpleNamespace(
            tasks=[task],
            local_couriers=[courier],
            movement_callback=_complete_routes,
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
            movement_callback=_complete_routes,
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

    def test_ramcom_bpt_is_mean_assignment_time_per_task(self) -> None:
        """RamCOM BPT should report mean assignment-decision time per task epoch."""

        tasks = [
            SimpleNamespace(num="t1", fare=10.0, s_time=0.0, d_time=10.0, weight=1.0, l_node="p1"),
            SimpleNamespace(num="t2", fare=10.0, s_time=0.0, d_time=10.0, weight=1.0, l_node="p2"),
        ]
        environment = SimpleNamespace(
            tasks=tasks,
            local_couriers=[],
            partner_couriers_by_platform={},
            movement_callback=_complete_routes,
            station_set=[],
            travel_model=SimpleNamespace(distance=lambda start, end: 0.0, travel_time=lambda start, end: 0.0),
            service_radius_km=None,
        )

        with (
            patch("baselines.ramcom.build_legacy_feasible_insertions", return_value=[]),
            patch("baselines.ramcom.perf_counter", side_effect=[0.0, 2.0, 3.0, 7.0]),
        ):
            result = run_ramcom_baseline_environment(environment=environment)

        self.assertEqual(result["BPT"], 3.0)

    def test_ramcom_acceptance_uses_reservation_when_history_missing(self) -> None:
        """RamCOM should use an explicit reservation model when empirical history is absent."""

        self.assertEqual(
            worker_acceptance_probability(
                payment=4.0,
                history_values=[],
                reservation_payment=8.0,
            ),
            0.5,
        )

    def test_ramcom_outer_payment_uses_reservation_candidates_without_history(self) -> None:
        """RamCOM outer payment should maximize expected revenue when workers lack history."""

        task = SimpleNamespace(fare=10.0)
        payment = choose_outer_payment_by_expected_revenue(
            task,
            outer_worker_histories=[[], []],
            reservation_payments=[4.0, 8.0],
        )

        self.assertEqual(payment, 4.0)

    def test_ramcom_can_assign_outer_worker_without_empirical_history(self) -> None:
        """A feasible outer courier with no history should still be evaluated by reservation acceptance."""

        task = SimpleNamespace(num="t1", fare=20.0, s_time=0.0, d_time=100.0, weight=1.0, l_node="p1")
        outer = SimpleNamespace(num=2, location="outer", re_schedule=[], re_weight=0.0, max_weight=5.0)
        environment = SimpleNamespace(
            tasks=[task],
            local_couriers=[],
            partner_couriers_by_platform={"P1": [outer]},
            movement_callback=_complete_routes,
            station_set=[],
            travel_model=SimpleNamespace(distance=lambda start, end: 0.0, travel_time=lambda start, end: 0.0),
            service_radius_km=None,
            geo_index=None,
            travel_speed_m_per_s=0.0,
        )

        def feasible_insertions(task: object, couriers: object, **_kwargs: object) -> list[object]:
            if couriers == [outer]:
                return [SimpleNamespace(courier=outer, insertion_index=0, distance_meters=0.0)]
            return []

        with (
            patch("baselines.ramcom.build_legacy_feasible_insertions", side_effect=feasible_insertions),
            patch("baselines.ramcom.drain_legacy_routes", return_value=1),
        ):
            result = run_ramcom_baseline_environment(environment=environment, random_seed=1)

        self.assertEqual(result["cross_assignment_count"], 1)
        self.assertEqual(result["partner_cross_assignment_counts"], {"P1": 1})

    def test_ramcom_reports_threshold_payment_and_trace_metadata(self) -> None:
        """RamCOM should expose threshold, acceptance model, payment search, and per-parcel trace."""

        task = SimpleNamespace(num="t1", fare=10.0, s_time=0.0, d_time=100.0, weight=1.0, l_node="p1")
        environment = SimpleNamespace(
            tasks=[task],
            local_couriers=[],
            partner_couriers_by_platform={},
            movement_callback=_complete_routes,
            station_set=[],
            travel_model=SimpleNamespace(distance=lambda start, end: 0.0, travel_time=lambda start, end: 0.0),
            service_radius_km=None,
            geo_index=None,
            travel_speed_m_per_s=0.0,
        )

        with patch("baselines.ramcom.build_legacy_feasible_insertions", return_value=[]):
            result = run_ramcom_baseline_environment(environment=environment, random_seed=1)

        self.assertEqual(result["method"], "RamCOM-CPUL")
        self.assertEqual(result["acceptance_model"], "empirical_history_or_reservation_based")
        self.assertEqual(result["payment_search"], "history_or_reservation_candidates")
        self.assertIn("theta", result)
        self.assertIn("k", result)
        self.assertIn("threshold", result)
        self.assertEqual(len(result["decision_trace"]), 1)
        self.assertEqual(result["decision_trace"][0]["branch"], "outer_no_candidate")

    def test_runner_builds_ramcom_batch_size_kwargs(self) -> None:
        """The root runner should pass batch-size configuration into RamCOM."""

        args = SimpleNamespace(
            algorithm="ramcom",
            batch_size=45,
            prediction_window_seconds=180,
            prediction_success_rate=0.8,
            prediction_sampling_seed=1,
            min_batch_size=10,
            max_batch_size=20,
            rl_batch_actions=None,
            step_seconds=60,
            episodes=1,
            rl_lr_actor=0.001,
            rl_lr_critic=0.001,
            rl_discount_factor=0.9,
            rl_entropy_coeff=0.01,
            rl_max_grad_norm=0.5,
            rl_disable_advantage_normalization=False,
            rl_future_feature_window_seconds=300,
            rl_device=None,
        )

        self.assertEqual(build_algorithm_kwargs(args), {"batch_size": 45})

    def test_ramcom_runner_keeps_trace_out_of_printed_metrics(self) -> None:
        """RamCOM runner should persist trace separately from the scalar metrics surface."""

        captured: dict[str, object] = {}

        def baseline_runner(**kwargs: object) -> dict[str, object]:
            captured["batch_size"] = kwargs["batch_size"]
            return {
                "TR": 0.0,
                "CR": 0.0,
                "BPT": 0.0,
                "accepted_assignments": 0,
                "local_assignment_count": 0,
                "cross_assignment_count": 0,
                "unresolved_parcel_count": 0,
                "partner_cross_assignment_counts": {},
                "partner_cross_revenues": {},
                "theta": 1,
                "k": 1,
                "threshold": 2.718281828459045,
                "max_fare": 1.0,
                "acceptance_model": "empirical_history_or_reservation_based",
                "payment_search": "history_or_reservation_candidates",
                "decision_trace": [{"parcel_id": "p1"}],
            }

        environment = SimpleNamespace(
            tasks=[],
            partner_couriers_by_platform={},
            partner_tasks_by_platform={},
        )
        summary = build_ramcom_runner(batch_size=45, baseline_runner=baseline_runner).run(environment=environment)

        self.assertEqual(captured["batch_size"], 45)
        self.assertNotIn("decision_trace", summary["metrics"])
        self.assertEqual(summary["decision_trace"], [{"parcel_id": "p1"}])


if __name__ == "__main__":
    unittest.main()
