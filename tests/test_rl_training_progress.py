"""Regression tests for RL-CAPA training progress reporting."""

from __future__ import annotations

import unittest

import torch

from capa.models import CAPAConfig
from rl_capa.config import RLCAPAConfig
from rl_capa.env import RLCAPAEnv
from rl_capa.trainer import RLCAPATrainer, TrainingConfig
from tests.test_rl_env_smoke import _seed, _task


class RLCAPATrainingProgressTests(unittest.TestCase):
    """Verify structured progress reporting for RL-CAPA training."""

    def test_trainer_emits_one_progress_event_per_episode(self) -> None:
        """Trainer should emit structured progress after each episode."""

        env = RLCAPAEnv(
            environment_seed=_seed([_task("now", "now-node")]),
            capa_config=CAPAConfig(),
            rl_config=RLCAPAConfig(min_batch_size=10, max_batch_size=10),
        )
        trainer = RLCAPATrainer(
            env=env,
            config=TrainingConfig(num_episodes=2, max_steps_per_episode=5),
            num_batch_actions=1,
        )
        events: list[dict[str, object]] = []

        trainer.train(
            batch_action_values=[10],
            progress_callback=lambda payload: events.append(dict(payload)),
        )

        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["episode"], 1)
        self.assertEqual(events[0]["total_episodes"], 2)
        self.assertIn("total_reward", events[0])
        self.assertIn("steps", events[0])
        self.assertIn("avg_batch_size", events[0])
        self.assertIn("entropy_pi1", events[0])
        self.assertIn("entropy_pi2", events[0])
        self.assertIn("truncated", events[0])

    def test_advantage_normalization_centers_and_scales_values(self) -> None:
        """Advantage normalization should stabilize actor loss scale without NaNs."""

        normalized = RLCAPATrainer._normalize_advantages(
            torch.tensor([1.0, 2.0, 3.0], dtype=torch.float32)
        )
        constant = RLCAPATrainer._normalize_advantages(
            torch.tensor([5.0, 5.0], dtype=torch.float32)
        )

        self.assertAlmostEqual(float(normalized.mean().item()), 0.0, places=6)
        self.assertAlmostEqual(float(normalized.std(unbiased=False).item()), 1.0, places=6)
        self.assertTrue(torch.all(torch.isfinite(constant)))


if __name__ == "__main__":
    unittest.main()
