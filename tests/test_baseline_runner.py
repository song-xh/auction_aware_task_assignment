"""Tests for unified Chengdu baseline experiment helpers."""

import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from baselines.greedy import parse_greedy_metrics, safe_average
from baselines.gta import (
    GTABid,
    count_available_couriers,
    is_idle_courier_feasible,
    legacy_courier_ready_state,
    select_available_courier_for_task,
    select_idle_courier_for_task,
    settle_aim_auction,
    should_bid_outer_platform_impgta,
    should_dispatch_inner_task_impgta,
)
from capa.experiments import (
    run_chengdu_basegta_baseline,
    run_chengdu_comparison_sweep,
    run_chengdu_greedy_baseline,
    run_chengdu_impgta_baseline,
)
from env.chengdu import LegacyChengduEnvironment


class _LinearTravelModel:
    """Provide deterministic distances and travel times for baseline tests."""

    def distance(self, start, end) -> float:
        """Return an absolute-distance metric in meters."""
        return float(abs(end - start))

    def travel_time(self, start, end) -> float:
        """Return the same linear metric as travel time in seconds."""
        return float(abs(end - start))


class BaselineRunnerTests(unittest.TestCase):
    """Validate the official baseline entrypoints without touching the real graph."""

    def test_select_idle_courier_prefers_lowest_dispatch_cost(self) -> None:
        """BaseGTA local assignment should prefer the cheapest idle feasible courier."""
        task = SimpleNamespace(l_node=4, d_time=100, weight=1.0)
        busy_courier = SimpleNamespace(num=9, location=1, re_schedule=[object()], re_weight=0.0, max_weight=5.0)
        far_courier = SimpleNamespace(num=2, location=10, re_schedule=[], re_weight=0.0, max_weight=5.0)
        near_courier = SimpleNamespace(num=1, location=2, re_schedule=[], re_weight=0.0, max_weight=5.0)

        bid = select_idle_courier_for_task(
            task=task,
            couriers=[busy_courier, far_courier, near_courier],
            travel_model=_LinearTravelModel(),
            now=0,
        )

        self.assertIsNotNone(bid)
        self.assertEqual(bid.courier.num, 1)

    def test_gta_feasibility_respects_service_radius(self) -> None:
        """BaseGTA and ImpGTA feasibility should reject idle couriers outside the configured service radius."""
        task = SimpleNamespace(l_node=4, d_time=100, weight=1.0)
        courier = SimpleNamespace(num=1, location=0, re_schedule=[], re_weight=0.0, max_weight=5.0)

        self.assertFalse(
            is_idle_courier_feasible(
                task=task,
                courier=courier,
                travel_model=_LinearTravelModel(),
                now=0,
                service_radius_meters=3.0,
            )
        )

    def test_basegta_runner_forwards_environment_geo_context(self) -> None:
        """BaseGTA should forward shared environment geo context into courier feasibility selection."""
        from baselines.gta import run_basegta_baseline_environment

        environment = SimpleNamespace(
            tasks=[SimpleNamespace(num="t1", l_node=10, s_time=0, d_time=100, weight=1.0, fare=10.0)],
            local_couriers=[],
            partner_couriers_by_platform={},
            station_set=[],
            travel_model=_LinearTravelModel(),
            movement_callback=lambda local, partner, seconds, station_set: None,
            service_radius_km=1.5,
            geo_index=object(),
            travel_speed_m_per_s=7.5,
        )

        with patch("baselines.gta.select_available_courier_for_task", return_value=None) as select_available:
            run_basegta_baseline_environment(environment=environment)

        self.assertIs(select_available.call_args.kwargs["geo_index"], environment.geo_index)
        self.assertEqual(select_available.call_args.kwargs["speed_m_per_s"], 7.5)

    def test_available_courier_selection_can_use_route_tail_state(self) -> None:
        """The Chengdu GTA adapter should evaluate couriers from their next available route state."""
        task = SimpleNamespace(l_node=12, d_time=100, weight=1.0)
        busy_courier = SimpleNamespace(
            num=1,
            location=0,
            re_schedule=[SimpleNamespace(l_node=10, reach_time=5.0)],
            re_weight=1.0,
            max_weight=5.0,
        )
        idle_courier = SimpleNamespace(num=2, location=20, re_schedule=[], re_weight=0.0, max_weight=5.0)

        ready_time, ready_location = legacy_courier_ready_state(busy_courier, now=0)
        bid = select_available_courier_for_task(
            task=task,
            couriers=[idle_courier, busy_courier],
            travel_model=_LinearTravelModel(),
            now=0,
        )

        self.assertEqual((ready_time, ready_location), (5.0, 10))
        self.assertIsNotNone(bid)
        self.assertEqual(bid.courier.num, 1)
        self.assertEqual(count_available_couriers([busy_courier, idle_courier], now=0, window_seconds=10), 2)

    def test_greedy_wrapper_respects_service_radius_in_unified_environment(self) -> None:
        """The unified Greedy runner should reject tasks outside the configured service radius."""
        from baselines.greedy import run_greedy_baseline_environment

        environment = SimpleNamespace(
            tasks=[SimpleNamespace(num="t1", l_node=4000, s_time=0, d_time=100, weight=1.0, fare=10.0)],
            local_couriers=[
                SimpleNamespace(
                    num=1,
                    location=0,
                    re_schedule=[],
                    re_weight=0.0,
                    max_weight=5.0,
                    w=0.5,
                    c=0.5,
                    station_num=1,
                )
            ],
            partner_couriers_by_platform={},
            station_set=[],
            travel_model=_LinearTravelModel(),
            movement_callback=lambda local, partner, seconds, station_set: None,
            service_radius_km=1.5,
        )

        metrics = run_greedy_baseline_environment(environment=environment, batch_size=300)

        self.assertEqual(metrics["TR"], 0.0)
        self.assertEqual(metrics["CR"], 0.0)

    def test_greedy_wrapper_forwards_environment_geo_context(self) -> None:
        """The unified Greedy runner should forward environment geo context into assignment selection."""
        from baselines.greedy import run_greedy_baseline_environment

        geo_index = object()
        environment = SimpleNamespace(
            tasks=[SimpleNamespace(num="t1", l_node=10, s_time=0, d_time=100, weight=1.0, fare=10.0)],
            local_couriers=[
                SimpleNamespace(
                    num=1,
                    location=0,
                    re_schedule=[],
                    re_weight=0.0,
                    max_weight=5.0,
                    w=0.5,
                    c=0.5,
                    station_num=1,
                    station=SimpleNamespace(l_node=0),
                )
            ],
            partner_couriers_by_platform={},
            station_set=[],
            travel_model=_LinearTravelModel(),
            movement_callback=lambda local, partner, seconds, station_set: None,
            service_radius_km=1.5,
            geo_index=geo_index,
            travel_speed_m_per_s=9.0,
        )

        with patch("baselines.greedy.select_greedy_assignment", return_value=None) as select_assignment:
            run_greedy_baseline_environment(environment=environment, batch_size=300)

        self.assertIs(select_assignment.call_args.kwargs["geo_index"], geo_index)
        self.assertEqual(select_assignment.call_args.kwargs["speed_m_per_s"], 9.0)

    def test_settle_aim_auction_uses_second_price_payment(self) -> None:
        """AIM should choose the lowest bidder and pay the second-lowest bid."""
        task = SimpleNamespace(fare=20.0)
        winner = settle_aim_auction(
            task=task,
            bids=[
                GTABid(platform_id="P1", courier=SimpleNamespace(num=1), dispatch_cost=6.0),
                GTABid(platform_id="P2", courier=SimpleNamespace(num=2), dispatch_cost=7.0),
                GTABid(platform_id="P3", courier=SimpleNamespace(num=3), dispatch_cost=8.0),
            ],
        )

        self.assertIsNotNone(winner)
        self.assertEqual(winner.platform_id, "P1")
        self.assertEqual(winner.dispatch_cost, 6.0)
        self.assertEqual(winner.payment, 7.0)

    def test_impgta_conditions_use_future_window_supply_and_reward(self) -> None:
        """ImpGTA should gate local and outer decisions by forecast supply-demand conditions."""
        task = SimpleNamespace(fare=8.0)
        future_tasks = [SimpleNamespace(fare=10.0), SimpleNamespace(fare=12.0)]

        self.assertFalse(should_dispatch_inner_task_impgta(task=task, idle_worker_count=1, future_tasks=future_tasks))
        self.assertTrue(should_dispatch_inner_task_impgta(task=SimpleNamespace(fare=12.0), idle_worker_count=1, future_tasks=future_tasks))
        self.assertFalse(
            should_bid_outer_platform_impgta(
                dispatch_cost=8.0,
                idle_worker_count=1,
                future_tasks=future_tasks,
            )
        )
        self.assertTrue(
            should_bid_outer_platform_impgta(
                dispatch_cost=12.0,
                idle_worker_count=1,
                future_tasks=future_tasks,
            )
        )

    def test_parse_greedy_metrics_reads_legacy_summary_line(self) -> None:
        """The parser should normalize the legacy Greedy summary line."""
        output = (
            "Greedy Result:-------------------------\n"
            "程序总耗时:0.11      ,完成任务个数:2    ,总失败个数:8    ,任务完成率:20.00%,"
            "所有均耗时:0.14    ms,成功均耗时:0.69    ms,所有总耗时:1.38      ms,批处理耗时:0.03    ms,"
            "任务均报价:6.86 ,平台总报价:13.71     ,平台总收益:2.29      \n"
        )

        metrics = parse_greedy_metrics(output)

        self.assertEqual(metrics["TR"], 2.29)
        self.assertEqual(metrics["CR"], 0.2)
        self.assertEqual(metrics["delivered_parcels"], 2)

    def test_parse_greedy_metrics_accepts_zero_success_spacing(self) -> None:
        """The parser should accept the zero-success summary format emitted by the legacy framework."""
        output = (
            "Greedy Result:-------------------------\n"
            "程序总耗时:0.08      ,完成任务个数:0    ,总失败个数:5    ,任务完成率:0.00 %,"
            "所有均耗时:0.00    ms,成功均耗时:0.00    ms,所有总耗时:0.00      ms,批处理耗时:0.00    ms,"
            "任务均报价:0.00 ,平台总报价:0.00      ,平台总收益:0.00      \n"
        )

        metrics = parse_greedy_metrics(output)

        self.assertEqual(metrics["TR"], 0.0)
        self.assertEqual(metrics["CR"], 0.0)
        self.assertEqual(metrics["delivered_parcels"], 0)

    def test_safe_average_returns_zero_for_empty_success_count(self) -> None:
        """Greedy aggregate logging should not divide by zero when no task is completed."""
        self.assertEqual(safe_average(10.0, 0), 0.0)
        self.assertEqual(safe_average(10.0, 2), 5.0)

    def test_run_chengdu_greedy_baseline_writes_summary(self) -> None:
        """The Greedy baseline helper should persist a summary with unified metric keys."""
        def fake_builder(**kwargs):
            return LegacyChengduEnvironment(
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
                "TR": 12.0,
                "CR": 0.8,
                "BPT": 1.5,
                "delivered_parcels": 8,
                "accepted_assignments": 8,
            }

        output_dir = Path("outputs/plots/test_greedy_baseline")
        summary = run_chengdu_greedy_baseline(
            data_dir=Path("Data"),
            num_parcels=10,
            local_courier_count=2,
            batch_size=300,
            output_dir=output_dir,
            env_builder=fake_builder,
            baseline_runner=fake_runner,
        )

        self.assertEqual(summary["metrics"]["TR"], 12.0)
        self.assertEqual(summary["metrics"]["delivered_parcels"], 8)
        self.assertTrue((output_dir / "summary.json").exists())

    def test_run_chengdu_basegta_baseline_writes_summary(self) -> None:
        """The BaseGTA baseline helper should persist a normalized summary."""
        def fake_builder(**kwargs):
            return LegacyChengduEnvironment(
                tasks=[],
                local_couriers=[],
                partner_couriers_by_platform={"P1": []},
                station_set=[],
                travel_model=None,
                platform_base_prices={"P1": 1.0},
                platform_sharing_rates={"P1": 0.4},
                platform_qualities={"P1": 1.0},
            )

        def fake_runner(**kwargs):
            return {
                "TR": 9.0,
                "CR": 0.7,
                "BPT": 0.5,
                "delivered_parcels": 7,
                "accepted_assignments": 7,
            }

        output_dir = Path("outputs/plots/test_basegta_baseline")
        summary = run_chengdu_basegta_baseline(
            data_dir=Path("Data"),
            num_parcels=10,
            local_courier_count=2,
            cooperating_platform_count=1,
            couriers_per_platform=1,
            output_dir=output_dir,
            env_builder=fake_builder,
            baseline_runner=fake_runner,
        )

        self.assertEqual(summary["algorithm"], "basegta")
        self.assertEqual(summary["metrics"]["TR"], 9.0)
        self.assertTrue((output_dir / "summary.json").exists())

    def test_run_chengdu_impgta_baseline_writes_summary(self) -> None:
        """The ImpGTA baseline helper should persist a normalized summary."""
        def fake_builder(**kwargs):
            return LegacyChengduEnvironment(
                tasks=[],
                local_couriers=[],
                partner_couriers_by_platform={"P1": []},
                station_set=[],
                travel_model=None,
                platform_base_prices={"P1": 1.0},
                platform_sharing_rates={"P1": 0.4},
                platform_qualities={"P1": 1.0},
            )

        def fake_runner(**kwargs):
            return {
                "TR": 11.0,
                "CR": 0.6,
                "BPT": 0.8,
                "delivered_parcels": 6,
                "accepted_assignments": 6,
            }

        output_dir = Path("outputs/plots/test_impgta_baseline")
        summary = run_chengdu_impgta_baseline(
            data_dir=Path("Data"),
            num_parcels=10,
            local_courier_count=2,
            cooperating_platform_count=1,
            couriers_per_platform=1,
            output_dir=output_dir,
            env_builder=fake_builder,
            baseline_runner=fake_runner,
        )

        self.assertEqual(summary["algorithm"], "impgta")
        self.assertEqual(summary["metrics"]["TR"], 11.0)
        self.assertTrue((output_dir / "summary.json").exists())

    def test_run_chengdu_comparison_sweep_writes_both_algorithms(self) -> None:
        """The comparison sweep should aggregate CAPA and baseline metrics over the same grid."""
        def fake_capa_runner(**kwargs):
            batch_size = kwargs["batch_size"]
            return {
                "algorithm": "capa",
                "metrics": {
                    "TR": float(batch_size),
                    "CR": 1.0,
                    "BPT": 2.0,
                    "delivered_parcels": 10,
                    "accepted_assignments": 10,
                },
            }

        def fake_baseline_runner(**kwargs):
            batch_size = kwargs["batch_size"]
            return {
                "algorithm": "greedy",
                "metrics": {
                    "TR": float(batch_size) - 1.0,
                    "CR": 0.9,
                    "BPT": 3.0,
                    "delivered_parcels": 9,
                    "accepted_assignments": 9,
                },
            }

        output_dir = Path("outputs/plots/test_comparison_sweep")
        summary = run_chengdu_comparison_sweep(
            data_dir=Path("Data"),
            output_dir=output_dir,
            sweep_parameter="batch_size",
            sweep_values=[300, 600],
            fixed_config={
                "num_parcels": 10,
                "local_courier_count": 2,
                "cooperating_platform_count": 1,
                "couriers_per_platform": 1,
                "batch_size": 300,
            },
            capa_runner=fake_capa_runner,
            baseline_runner=fake_baseline_runner,
        )

        self.assertEqual(len(summary["runs"]), 2)
        self.assertEqual(summary["runs"][0]["capa"]["metrics"]["TR"], 300.0)
        self.assertEqual(summary["runs"][0]["greedy"]["metrics"]["TR"], 299.0)
        self.assertTrue((output_dir / "summary.json").exists())


if __name__ == "__main__":
    unittest.main()
