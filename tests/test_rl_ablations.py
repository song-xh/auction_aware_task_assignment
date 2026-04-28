"""Regression tests for RL-CAPA ablation trainers and comparison plots."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from algorithms.registry import get_algorithm_names
from capa.models import CAPAConfig
from rl_capa.config import RLCAPAConfig, RLTrainingConfig


class RLCAPAAblationTests(unittest.TestCase):
    """Verify RL-CAPA ablation variants are first-class runnable algorithms."""

    def setUp(self) -> None:
        """Create one temporary output root."""

        self.temp_root = Path(tempfile.mkdtemp(prefix="rl_capa_ablation_tests_"))

    def tearDown(self) -> None:
        """Remove temporary outputs."""

        shutil.rmtree(self.temp_root, ignore_errors=True)

    def test_stage1_algorithm_is_registered(self) -> None:
        """Stage-1-only ablation should be selectable through the registry."""

        self.assertIn("rl-capa-stage1", get_algorithm_names())

    def test_train_stage1_summary_contains_reward_curve(self) -> None:
        """Stage-1 training summary should expose reward history and a plot."""

        from rl_capa.stage1_trainer import Stage1EpisodeLog
        from rl_capa.train_stage1 import train_stage1_rl_capa

        history = [
            Stage1EpisodeLog(
                episode=0,
                total_reward=10.0,
                loss_pi1=1.0,
                loss_v1=2.0,
                steps=1,
                assignments=1,
                batch_sizes=[10],
                mean_batch_size=10.0,
            )
        ]

        with patch("rl_capa.train_stage1.RLCAPAEnv"), patch(
            "rl_capa.train_stage1.Stage1RLCAPATrainer",
        ) as trainer_cls, patch(
            "rl_capa.train_stage1.plot_training_curves",
            return_value=self.temp_root / "stage1_training.png",
        ):
            trainer = trainer_cls.return_value
            trainer.train.return_value = history
            trainer.device = "cpu"

            summary = train_stage1_rl_capa(
                environment_seed=SimpleNamespace(),
                capa_config=CAPAConfig(),
                rl_config=RLCAPAConfig(min_batch_size=10, max_batch_size=10),
                training_config=RLTrainingConfig(episodes=1),
                output_dir=self.temp_root,
            )

        self.assertEqual(summary["episode_returns"], [10.0])
        self.assertEqual(summary["mean_batch_size"], [10.0])
        self.assertIn("training_curves", summary["plots"])


if __name__ == "__main__":
    unittest.main()
