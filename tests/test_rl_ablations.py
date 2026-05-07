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

    def test_stage2_algorithm_is_registered(self) -> None:
        """Stage-2-only ablation should be selectable through the registry."""

        self.assertIn("rl-capa-stage2", get_algorithm_names())

    def test_ablation_algorithm_is_registered(self) -> None:
        """Combined ablation runner should be selectable through the registry."""

        self.assertIn("rl-capa-ablation", get_algorithm_names())

    def test_plot_reward_comparison_creates_file(self) -> None:
        """Reward comparison plot should combine full and ablation histories."""

        from rl_capa.ablation_compare import plot_reward_comparison

        output_path = plot_reward_comparison(
            reward_histories={
                "rl-capa": [1.0, 2.0],
                "rl-capa-stage1": [0.5, 1.5],
                "rl-capa-stage2": [0.25, 1.25],
            },
            output_path=self.temp_root / "reward_comparison.png",
        )

        self.assertTrue(output_path.exists())

    def test_plot_reward_comparison_uses_smoothed_band_instead_of_raw_lines(self) -> None:
        """Reward comparison plot should render one mean line and one band per variant."""

        from rl_capa.visualize import _configure_matplotlib_cache
        from rl_capa.ablation_compare import plot_reward_comparison

        _configure_matplotlib_cache()
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot

        with patch("matplotlib.axes.Axes.plot") as plot_line, patch(
            "matplotlib.axes.Axes.fill_between",
        ) as fill_between:
            plot_reward_comparison(
                reward_histories={
                    "rl-capa": [1.0, 8.0, 2.0, 9.0],
                    "rl-capa-stage1": [0.5, 5.0, 1.5, 6.0],
                    "rl-capa-stage2": [0.25, 3.0, 1.25, 4.0],
                },
                output_path=self.temp_root / "reward_comparison.png",
                window=3,
            )

        self.assertEqual(plot_line.call_count, 3)
        self.assertEqual(fill_between.call_count, 3)
        for call in fill_between.call_args_list:
            self.assertGreaterEqual(call.kwargs["alpha"], 0.15)
            self.assertLessEqual(call.kwargs["alpha"], 0.25)

    def test_plot_reward_comparison_scales_ylim_to_reward_history(self) -> None:
        """Reward comparison plot should keep the y-axis wide enough for the actual rewards."""

        from rl_capa.visualize import _configure_matplotlib_cache
        from rl_capa.ablation_compare import plot_reward_comparison

        _configure_matplotlib_cache()
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot

        with patch("matplotlib.axes.Axes.set_ylim") as set_ylim:
            plot_reward_comparison(
                reward_histories={
                    "rl-capa": [1000.0, 1800.0],
                    "rl-capa-stage1": [1200.0, 1500.0],
                    "rl-capa-stage2": [1100.0, 1900.0],
                },
                output_path=self.temp_root / "reward_comparison.png",
                window=2,
            )

        lower, upper = set_ylim.call_args.args
        self.assertLessEqual(lower, 10.0)
        self.assertGreaterEqual(upper, 19.0)

    def test_combined_ablation_runner_returns_reward_plot(self) -> None:
        """Combined runner should train all variants and expose the merged plot."""

        from algorithms.rl_capa_ablation_runner import build_rl_capa_ablation_runner

        runner = build_rl_capa_ablation_runner(batch_actions=[10, 15], fixed_batch_size=30, episodes=1)
        with patch("algorithms.rl_capa_ablation_runner.build_environment_seed", return_value=SimpleNamespace()), patch(
            "algorithms.rl_capa_ablation_runner.train_rl_capa",
            return_value={"episode_returns": [1.0], "plots": {}},
        ), patch(
            "algorithms.rl_capa_ablation_runner.train_stage1_rl_capa",
            return_value={"episode_returns": [0.8], "plots": {}},
        ), patch(
            "algorithms.rl_capa_ablation_runner.train_stage2_rl_capa",
            return_value={"episode_returns": [0.6], "plots": {}},
        ), patch(
            "algorithms.rl_capa_ablation_runner.plot_reward_comparison",
            return_value=self.temp_root / "reward_comparison.png",
        ):
            summary = runner.run(environment=SimpleNamespace(), output_dir=self.temp_root)

        self.assertIn("reward_comparison", summary["plots"])
        self.assertEqual(set(summary["training"]), {"rl-capa", "rl-capa-stage1", "rl-capa-stage2"})

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

    def test_train_stage2_summary_contains_reward_curve(self) -> None:
        """Stage-2 training summary should expose reward and cross-rate history."""

        from rl_capa.stage2_trainer import Stage2EpisodeLog
        from rl_capa.train_stage2 import train_stage2_rl_capa

        history = [
            Stage2EpisodeLog(
                episode=0,
                total_reward=8.0,
                loss_pi2=1.0,
                loss_v2=2.0,
                steps=1,
                assignments=1,
                fixed_batch_size=30,
                cross_rate=0.5,
                mean_batch_size=30.0,
            )
        ]

        with patch("rl_capa.train_stage2.RLCAPAEnv"), patch(
            "rl_capa.train_stage2.Stage2RLCAPATrainer",
        ) as trainer_cls, patch(
            "rl_capa.train_stage2.plot_training_curves",
            return_value=self.temp_root / "stage2_training.png",
        ):
            trainer = trainer_cls.return_value
            trainer.train.return_value = history
            trainer.device = "cpu"

            summary = train_stage2_rl_capa(
                environment_seed=SimpleNamespace(),
                capa_config=CAPAConfig(),
                rl_config=RLCAPAConfig(min_batch_size=30, max_batch_size=30),
                training_config=RLTrainingConfig(episodes=1),
                fixed_batch_size=30,
                output_dir=self.temp_root,
            )

        self.assertEqual(summary["episode_returns"], [8.0])
        self.assertEqual(summary["cross_rate"], [0.5])
        self.assertEqual(summary["mean_batch_size"], [30.0])
        self.assertIn("training_curves", summary["plots"])


if __name__ == "__main__":
    unittest.main()
