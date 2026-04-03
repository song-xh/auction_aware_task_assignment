"""Tests for the RL-CAPA environment wrapper."""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from capa.models import CAPAConfig
from env.chengdu import ChengduEnvironment
from experiments.seeding import build_environment_seed


class _LinearTravelModel:
    """Provide deterministic distances and travel times for RL environment tests."""

    def distance(self, start: object, end: object) -> float:
        """Return an absolute-distance metric in meters."""
        return float(abs(int(end) - int(start)))

    def travel_time(self, start: object, end: object) -> float:
        """Return the same linear metric as travel time in seconds."""
        return self.distance(start, end)


class RLCAPAEnvironmentTests(unittest.TestCase):
    """Validate the shared Chengdu-backed RL environment behavior."""

    @staticmethod
    def _drain_one_step(local, partner, seconds, station_set) -> None:
        """Pop one queued task per courier so drain-based tests can terminate."""
        for courier in [*local, *partner]:
            if getattr(courier, "re_schedule", []):
                head = courier.re_schedule.pop(0)
                courier.location = head.l_node
                courier.re_weight = max(0.0, float(getattr(courier, "re_weight", 0.0)) - float(getattr(head, "weight", 0.0)))

    def test_cross_action_yields_immediate_cross_reward(self) -> None:
        """A parcel sent to DAPA and matched should produce a positive immediate M_m reward."""
        from rl_capa.config import RLCAPAConfig
        from rl_capa.env import RLCAPAEnvironment

        environment = ChengduEnvironment(
            tasks=[SimpleNamespace(num="t1", l_node=1, s_time=0, d_time=100, weight=1.0, fare=10.0)],
            local_couriers=[],
            partner_couriers_by_platform={
                "P1": [SimpleNamespace(num=1, location=0, station=SimpleNamespace(l_node=0), station_num=1, re_schedule=[], re_weight=0.0, max_weight=5.0, w=0.4, c=0.6, service_score=0.8)]
            },
            station_set=[SimpleNamespace(num=1, l_node=0)],
            travel_model=_LinearTravelModel(),
            platform_base_prices={"P1": 1.0},
            platform_sharing_rates={"P1": 0.4},
            platform_qualities={"P1": 1.0},
            movement_callback=self._drain_one_step,
        )

        env = RLCAPAEnvironment(
            environment_seed=build_environment_seed(environment),
            capa_config=CAPAConfig(batch_size=60),
            rl_config=RLCAPAConfig(min_batch_size=60, max_batch_size=60, step_seconds=10),
        )
        env.reset()
        context = env.start_batch(batch_duration=60)
        result = env.apply_parcel_actions(context, {"t1": 1})

        self.assertEqual(len(context.auction_pool), 1)
        self.assertEqual(result.batch_transition.reward, result.batch_reward)
        self.assertGreater(result.batch_reward, 0.0)
        self.assertEqual(len(result.parcel_transitions), 1)
        self.assertGreater(result.parcel_transitions[0].reward, 0.0)

    def test_defer_action_yields_zero_immediate_reward_and_carries_parcel(self) -> None:
        """A deferred parcel should receive zero immediate M_m reward and reappear next batch."""
        from rl_capa.config import RLCAPAConfig
        from rl_capa.env import RLCAPAEnvironment

        environment = ChengduEnvironment(
            tasks=[SimpleNamespace(num="t1", l_node=1, s_time=0, d_time=100, weight=1.0, fare=10.0)],
            local_couriers=[],
            partner_couriers_by_platform={},
            station_set=[],
            travel_model=_LinearTravelModel(),
            platform_base_prices={},
            platform_sharing_rates={},
            platform_qualities={},
            movement_callback=self._drain_one_step,
        )

        env = RLCAPAEnvironment(
            environment_seed=build_environment_seed(environment),
            capa_config=CAPAConfig(batch_size=60),
            rl_config=RLCAPAConfig(min_batch_size=60, max_batch_size=60, step_seconds=10),
        )
        env.reset()
        context = env.start_batch(batch_duration=60)
        result = env.apply_parcel_actions(context, {"t1": 0})
        next_context = env.start_batch(batch_duration=60)

        self.assertEqual(tuple(result.parcel_transitions), ())
        self.assertEqual(result.batch_reward, 0.0)
        self.assertEqual(len(next_context.resolved_parcel_transitions), 1)
        self.assertEqual(next_context.resolved_parcel_transitions[0].reward, 0.0)
        self.assertEqual(int(next_context.batch_state[0]), 1)


if __name__ == "__main__":
    unittest.main()
