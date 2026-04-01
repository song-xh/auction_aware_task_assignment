"""Tests for paper-faithful local-platform revenue accounting across baselines."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from env.chengdu import ChengduEnvironment


class _LinearTravelModel:
    """Provide deterministic distances and travel times for revenue-accounting tests."""

    def distance(self, start, end) -> float:
        """Return an absolute-distance metric in meters."""
        return float(abs(end - start))

    def travel_time(self, start, end) -> float:
        """Return the same linear metric as travel time in seconds."""
        return float(abs(end - start))


class BaselineRevenueTests(unittest.TestCase):
    """Validate that baseline TR follows the CPUL net-revenue definition."""

    @staticmethod
    def _drain_one_step(local, partner, seconds, station_set) -> None:
        """Pop one queued task per courier so drain-based tests can terminate."""
        for courier in [*local, *partner]:
            if getattr(courier, "re_schedule", []):
                courier.re_schedule.pop(0)

    def test_basegta_local_revenue_uses_fixed_local_payment_ratio(self) -> None:
        """BaseGTA local completions should use `p_tau - zeta * p_tau` under the CPUL metric."""
        from baselines.gta import run_basegta_baseline_environment

        environment = ChengduEnvironment(
            tasks=[SimpleNamespace(num="t1", l_node=1, s_time=0, d_time=100, weight=1.0, fare=10.0)],
            local_couriers=[SimpleNamespace(num=1, location=0, re_schedule=[], re_weight=0.0, max_weight=5.0)],
            partner_couriers_by_platform={},
            station_set=[],
            travel_model=_LinearTravelModel(),
            platform_base_prices={},
            platform_sharing_rates={},
            platform_qualities={},
            movement_callback=self._drain_one_step,
        )

        metrics = run_basegta_baseline_environment(environment=environment, unit_price_per_km=3.0)

        self.assertEqual(metrics["TR"], 8.0)
        self.assertEqual(metrics["CR"], 1.0)

    def test_basegta_outer_revenue_uses_payment_not_dispatch_cost(self) -> None:
        """BaseGTA cooperative revenue should subtract the AIM payment rather than the winner's raw cost."""
        from baselines.gta import run_basegta_baseline_environment

        environment = ChengduEnvironment(
            tasks=[SimpleNamespace(num="t1", l_node=0, s_time=0, d_time=5000, weight=1.0, fare=20.0)],
            local_couriers=[],
            partner_couriers_by_platform={
                "P1": [SimpleNamespace(num=1, location=1000, re_schedule=[], re_weight=0.0, max_weight=5.0)],
                "P2": [SimpleNamespace(num=2, location=2000, re_schedule=[], re_weight=0.0, max_weight=5.0)],
            },
            station_set=[],
            travel_model=_LinearTravelModel(),
            platform_base_prices={"P1": 1.0, "P2": 1.0},
            platform_sharing_rates={"P1": 0.4, "P2": 0.4},
            platform_qualities={"P1": 1.0, "P2": 1.0},
            movement_callback=self._drain_one_step,
        )

        metrics = run_basegta_baseline_environment(environment=environment, unit_price_per_km=1.0)

        self.assertEqual(metrics["TR"], 18.0)
        self.assertEqual(metrics["CR"], 1.0)

    def test_mra_local_revenue_uses_fixed_local_payment_ratio(self) -> None:
        """MRA's evaluation revenue should follow the CPUL local-payment rule."""
        from baselines.mra import run_mra_baseline_environment

        environment = ChengduEnvironment(
            tasks=[SimpleNamespace(num="t1", l_node=1, s_time=0, d_time=100, weight=1.0, fare=10.0)],
            local_couriers=[SimpleNamespace(num=1, location=0, re_schedule=[], re_weight=0.0, max_weight=5.0)],
            partner_couriers_by_platform={},
            station_set=[],
            travel_model=_LinearTravelModel(),
            platform_base_prices={},
            platform_sharing_rates={},
            platform_qualities={},
            movement_callback=self._drain_one_step,
        )

        metrics = run_mra_baseline_environment(environment=environment, batch_size=60)

        self.assertEqual(metrics["TR"], 8.0)
        self.assertEqual(metrics["CR"], 1.0)

    def test_ramcom_inner_revenue_uses_fixed_local_payment_ratio(self) -> None:
        """RamCOM inner-worker completions should use the same local-platform net-revenue rule."""
        from baselines.ramcom import run_ramcom_baseline_environment

        environment = ChengduEnvironment(
            tasks=[SimpleNamespace(num="t1", l_node=1, s_time=0, d_time=100, weight=1.0, fare=10.0)],
            local_couriers=[
                SimpleNamespace(num=1, location=0, re_schedule=[], re_weight=0.0, max_weight=5.0, history_completed_values=[3.0, 5.0])
            ],
            partner_couriers_by_platform={},
            station_set=[],
            travel_model=_LinearTravelModel(),
            platform_base_prices={},
            platform_sharing_rates={},
            platform_qualities={},
            movement_callback=self._drain_one_step,
        )

        with patch("baselines.ramcom.random.Random.randint", return_value=1):
            metrics = run_ramcom_baseline_environment(environment=environment, random_seed=7)

        self.assertEqual(metrics["TR"], 8.0)
        self.assertEqual(metrics["CR"], 1.0)


if __name__ == "__main__":
    unittest.main()
