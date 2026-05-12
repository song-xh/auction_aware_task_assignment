"""Regression for P4 domain-randomized RL-CAPA training hook (review_0512.md)."""

from __future__ import annotations

import random
import unittest
from types import SimpleNamespace
from typing import Mapping

from capa.models import CAPAConfig
from env.chengdu import ChengduEnvironment
from experiments.seeding import build_environment_seed
from rl_capa.config import RLCAPAConfig
from rl_capa.env import RLCAPAEnv


def _seed_with_one_task() -> tuple[SimpleNamespace, object]:
    """Build a single-task Chengdu seed and return ``(task_proto, seed)``.

    The task prototype is returned so tests can confirm the seed clone is
    mutated independently of the original.
    """

    task = SimpleNamespace(
        num="t1",
        s_time=0.0,
        d_time=100.0,
        weight=1.0,
        fare=10.0,
        l_node="A",
    )
    environment = ChengduEnvironment(
        tasks=[task],
        local_couriers=[],
        partner_couriers_by_platform={},
        station_set=[],
        travel_model=None,
        platform_base_prices={},
        platform_sharing_rates={},
        platform_qualities={},
    )
    return task, build_environment_seed(environment)


class DisturbanceSamplerTests(unittest.TestCase):
    """``RLCAPAEnv`` must invoke the sampler once per ``reset()``."""

    def test_sampler_called_per_reset_and_records_last_disturbance(self) -> None:
        _, seed = _seed_with_one_task()
        capa_config = CAPAConfig()
        rl_config = RLCAPAConfig(
            min_batch_size=10,
            max_batch_size=10,
            batch_actions=[10],
            step_seconds=10,
        )
        observed: list[Mapping[str, float]] = []

        def sampler(episode_idx: int, rng: random.Random) -> Mapping[str, float]:
            del rng
            payload = {"delay_seconds": 20.0 + episode_idx, "noise_percent": 5.0 * episode_idx}
            observed.append(payload)
            return payload

        env = RLCAPAEnv(
            environment_seed=seed,
            capa_config=capa_config,
            rl_config=rl_config,
            disturbance_sampler=sampler,
        )

        env.reset()
        first = dict(env.last_disturbance)
        env.reset()
        second = dict(env.last_disturbance)

        self.assertEqual(len(observed), 2)
        self.assertEqual(first, {"delay_seconds": 20.0, "noise_percent": 0.0})
        self.assertEqual(second, {"delay_seconds": 21.0, "noise_percent": 5.0})

    def test_no_sampler_keeps_environment_clean(self) -> None:
        _, seed = _seed_with_one_task()
        env = RLCAPAEnv(
            environment_seed=seed,
            capa_config=CAPAConfig(),
            rl_config=RLCAPAConfig(
                min_batch_size=10,
                max_batch_size=10,
                batch_actions=[10],
                step_seconds=10,
            ),
        )

        env.reset()

        self.assertEqual(env.last_disturbance, {"delay_seconds": 0.0, "noise_percent": 0.0})

    def test_sampler_mutates_only_cloned_environment(self) -> None:
        original_task, seed = _seed_with_one_task()

        def sampler(episode_idx: int, rng: random.Random) -> Mapping[str, float]:
            del episode_idx, rng
            return {"delay_seconds": 5.0, "noise_percent": 10.0}

        env = RLCAPAEnv(
            environment_seed=seed,
            capa_config=CAPAConfig(),
            rl_config=RLCAPAConfig(
                min_batch_size=10,
                max_batch_size=10,
                batch_actions=[10],
                step_seconds=10,
            ),
            disturbance_sampler=sampler,
        )

        env.reset()

        self.assertFalse(hasattr(original_task, "observed_s_time"))
        self.assertFalse(hasattr(original_task, "observed_d_time"))


if __name__ == "__main__":
    unittest.main()
