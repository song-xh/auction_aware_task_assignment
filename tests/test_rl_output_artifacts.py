"""Regression tests for RL-CAPA plot artifacts and summary wiring."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from algorithms.rl_capa_runner import build_rl_capa_runner
from capa.models import CAPAConfig
from rl_capa.config import RLCAPAConfig, RLTrainingConfig
from rl_capa.evaluate import evaluate_rl_capa
from rl_capa.train import train_rl_capa
from rl_capa.trainer import EpisodeLog


class RLCAPAOutputArtifactTests(unittest.TestCase):
    """Verify RL-CAPA writes plot metadata alongside numeric outputs."""

    def setUp(self) -> None:
        self.temp_root = Path(tempfile.mkdtemp(prefix="rl_capa_plots_"))

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_root, ignore_errors=True)

    def test_train_rl_capa_includes_training_plot_path(self) -> None:
        """Training summary should expose the generated training-curve artifact."""

        history = [
            EpisodeLog(
                episode=0,
                total_reward=10.0,
                loss_pi1=1.0,
                loss_pi2=2.0,
                loss_v1=3.0,
                loss_v2=4.0,
                steps=5,
                assignments=4,
                batch_sizes=[10, 15],
                cross_rate=0.5,
                mean_batch_size=12.5,
            )
        ]

        with patch("rl_capa.train.RLCAPAEnv"), patch("rl_capa.train.RLCAPATrainer") as trainer_cls, patch(
            "rl_capa.train.plot_training_curves",
            create=True,
            return_value=self.temp_root / "training_curves.png",
        ) as plot_curves:
            trainer = trainer_cls.return_value
            trainer.train.return_value = history
            trainer.device = "cpu"

            summary = train_rl_capa(
                environment_seed=SimpleNamespace(),
                capa_config=CAPAConfig(),
                rl_config=RLCAPAConfig(min_batch_size=10, max_batch_size=10),
                training_config=RLTrainingConfig(episodes=1),
                output_dir=self.temp_root,
            )

        self.assertIn("plots", summary)
        self.assertEqual(summary["plots"]["training_curves"], str(self.temp_root / "training_curves.png"))
        self.assertEqual(summary["entropy_pi1"], [0.0])
        self.assertEqual(summary["entropy_pi2"], [0.0])
        self.assertEqual(summary["mean_batch_size"], [12.5])
        plot_curves.assert_called_once()

    def test_training_curves_use_smoothed_bands_instead_of_raw_lines(self) -> None:
        """Training curves should render one smoothed line and one band per plotted series."""

        from rl_capa.visualize import _configure_matplotlib_cache, plot_training_curves

        _configure_matplotlib_cache()
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot

        history = [
            EpisodeLog(
                episode=index,
                total_reward=float(value),
                loss_pi1=float(index + 1),
                loss_pi2=float(index + 2),
                loss_v1=float(index + 3),
                loss_v2=float(index + 4),
                steps=5,
                assignments=4,
                batch_sizes=[10, 15],
                cross_rate=0.25 + index * 0.05,
                mean_batch_size=12.5 + index,
                entropy_pi1=0.1 + index * 0.01,
                entropy_pi2=0.2 + index * 0.01,
            )
            for index, value in enumerate([10.0, 30.0, 12.0, 28.0])
        ]

        with patch("matplotlib.axes.Axes.plot") as plot_line, patch(
            "matplotlib.axes.Axes.fill_between",
        ) as fill_between:
            plot_training_curves(
                history=history,
                output_path=self.temp_root / "training_curves.png",
                window=3,
            )

        self.assertEqual(plot_line.call_count, 9)
        self.assertEqual(fill_between.call_count, 9)
        for call in fill_between.call_args_list:
            self.assertGreaterEqual(call.kwargs["alpha"], 0.15)
            self.assertLessEqual(call.kwargs["alpha"], 0.25)

    def test_evaluate_rl_capa_includes_batch_plot_paths(self) -> None:
        """Evaluation summary should expose TR/CR/BPT plot artifacts."""

        fake_env = SimpleNamespace(
            batch_reports=lambda: [SimpleNamespace()],
            delivered_parcels=lambda: ["p1", "p2"],
            accepted_assignments=lambda: ["a1", "a2"],
            timed_out_parcels=lambda: [],
        )
        fake_result = SimpleNamespace(
            total_revenue=12.0,
            completion_rate=0.5,
            batch_processing_time=0.25,
            total_parcels=4,
            assignments=2,
            steps=1,
        )

        with patch("rl_capa.evaluate.RLCAPAEnv", return_value=fake_env), patch(
            "rl_capa.evaluate.RLCAPATrainer.load_checkpoint",
            return_value=SimpleNamespace(),
        ), patch("rl_capa.evaluate.evaluate", return_value=fake_result), patch(
            "rl_capa.evaluate.plot_evaluation_curves",
            create=True,
            return_value={
                "TR": str(self.temp_root / "eval" / "tr_over_batches.png"),
                "CR": str(self.temp_root / "eval" / "cr_over_batches.png"),
                "BPT": str(self.temp_root / "eval" / "bpt_over_batches.png"),
            },
        ) as plot_eval:
            summary = evaluate_rl_capa(
                environment_seed=SimpleNamespace(),
                capa_config=CAPAConfig(),
                rl_config=RLCAPAConfig(min_batch_size=10, max_batch_size=10),
                checkpoint_dir=self.temp_root / "checkpoints",
                output_dir=self.temp_root / "eval",
                training_config=RLTrainingConfig(episodes=1),
            )

        self.assertIn("plots", summary)
        self.assertIn("TR", summary["plots"])
        self.assertIn("CR", summary["plots"])
        self.assertIn("BPT", summary["plots"])
        plot_eval.assert_called_once()

    def test_rl_runner_summary_links_training_and_evaluation_plots(self) -> None:
        """Top-level RL-CAPA summary should surface both plot groups."""

        runner = build_rl_capa_runner(batch_actions=[10, 15, 20], episodes=1)

        with patch("algorithms.rl_capa_runner.build_environment_seed", return_value=SimpleNamespace()), patch(
            "algorithms.rl_capa_runner.train_rl_capa",
            return_value={
                "episode_returns": [1.0],
                "plots": {"training_curves": str(self.temp_root / "training_curves.png")},
            },
        ), patch(
            "algorithms.rl_capa_runner.evaluate_rl_capa",
            return_value={
                "metrics": {"TR": 5.0, "CR": 1.0, "BPT": 0.1},
                "plots": {
                    "TR": str(self.temp_root / "eval" / "tr_over_batches.png"),
                    "CR": str(self.temp_root / "eval" / "cr_over_batches.png"),
                    "BPT": str(self.temp_root / "eval" / "bpt_over_batches.png"),
                },
            },
        ):
            summary = runner.run(
                environment=SimpleNamespace(),
                output_dir=self.temp_root / "run",
            )

        self.assertIn("plots", summary)
        self.assertIn("training", summary["plots"])
        self.assertIn("evaluation", summary["plots"])
        self.assertIn("training_curves", summary["plots"]["training"])
        self.assertIn("TR", summary["plots"]["evaluation"])


if __name__ == "__main__":
    unittest.main()
