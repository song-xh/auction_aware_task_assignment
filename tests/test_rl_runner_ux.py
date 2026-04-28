"""Focused RL-CAPA runner UX regression tests."""

from __future__ import annotations

import unittest
from pathlib import Path

from rl_capa.config import RLCAPAConfig
from runner import build_algorithm_kwargs, parse_args


class RLCAPARunnerUXTests(unittest.TestCase):
    """Verify RL-CAPA runner config parsing and action-space translation."""

    def test_rl_config_prefers_explicit_batch_actions(self) -> None:
        """Explicit RL batch actions should override the legacy contiguous range."""

        config = RLCAPAConfig(
            min_batch_size=10,
            max_batch_size=20,
            batch_actions=(10, 15, 20),
        )

        self.assertEqual(config.batch_action_values(), [10, 15, 20])
        self.assertEqual(config.batch_duration_from_action_index(1), 15)
        self.assertEqual(config.batch_duration_to_action_index(20), 2)

    def test_rl_config_rejects_non_positive_explicit_batch_actions(self) -> None:
        """Explicit RL batch actions must all be positive durations."""

        config = RLCAPAConfig(
            min_batch_size=10,
            max_batch_size=20,
            batch_actions=(10, 0, 20),
        )

        with self.assertRaises(ValueError):
            config.batch_action_values()

    def test_runner_build_kwargs_include_explicit_rl_batch_actions(self) -> None:
        """Runner argument translation should forward explicit RL batch actions."""

        args = parse_args(
            [
                "run",
                "--algorithm",
                "rl-capa",
                "--data-dir",
                "Data",
                "--rl-batch-actions",
                "10",
                "15",
                "20",
            ]
        )

        kwargs = build_algorithm_kwargs(args)

        self.assertEqual(kwargs["batch_actions"], [10, 15, 20])
        self.assertTrue(kwargs["normalize_advantages"])

    def test_runner_build_kwargs_include_stage1_ablation_rl_params(self) -> None:
        """Stage-1 ablation should receive the same RL hyperparameters as RL-CAPA."""

        args = parse_args(
            [
                "run",
                "--algorithm",
                "rl-capa-stage1",
                "--data-dir",
                "Data",
                "--rl-batch-actions",
                "10",
                "15",
                "--episodes",
                "3",
            ]
        )

        kwargs = build_algorithm_kwargs(args)

        self.assertEqual(kwargs["batch_actions"], [10, 15])
        self.assertEqual(kwargs["episodes"], 3)
        self.assertTrue(kwargs["normalize_advantages"])

    def test_runner_build_kwargs_include_stage2_fixed_batch_size(self) -> None:
        """Stage-2 ablation should receive fixed batch-size and RL hyperparameters."""

        args = parse_args(
            [
                "run",
                "--algorithm",
                "rl-capa-stage2",
                "--data-dir",
                "Data",
                "--batch-size",
                "30",
                "--episodes",
                "3",
            ]
        )

        kwargs = build_algorithm_kwargs(args)

        self.assertEqual(kwargs["fixed_batch_size"], 30)
        self.assertEqual(kwargs["episodes"], 3)
        self.assertTrue(kwargs["normalize_advantages"])

    def test_runner_can_disable_rl_advantage_normalization(self) -> None:
        """Runner should expose an ablation switch for actor advantage scaling."""

        args = parse_args(
            [
                "run",
                "--algorithm",
                "rl-capa",
                "--data-dir",
                "Data",
                "--rl-disable-advantage-normalization",
            ]
        )

        kwargs = build_algorithm_kwargs(args)

        self.assertFalse(kwargs["normalize_advantages"])

    def test_runner_parses_partner_history_task_controls(self) -> None:
        """Runner should expose explicit partner-history task controls for dense windows."""

        args = parse_args(
            [
                "run",
                "--algorithm",
                "rl-capa",
                "--data-dir",
                "Data",
                "--partner-history-task-count-start",
                "200",
                "--partner-history-task-count-step",
                "0",
            ]
        )

        self.assertEqual(args.partner_history_task_count_start, 200)
        self.assertEqual(args.partner_history_task_count_step, 0)

    def test_readme_documents_dense_smoke_window_for_rl_capa(self) -> None:
        """README should document the dense 0-30s RL-CAPA smoke recipe."""

        readme = Path("README.md").read_text(encoding="utf-8")

        self.assertIn("--task-window-start-seconds 0", readme)
        self.assertIn("--task-window-end-seconds 30", readme)
        self.assertIn("--rl-batch-actions 10 15 20", readme)

    def test_readme_documents_stable_rl_capa_diagnostic_recipe(self) -> None:
        """README should document a less saturated RL-CAPA training recipe."""

        readme = Path("README.md").read_text(encoding="utf-8")

        self.assertIn("RL-CAPA 稳定诊断配方", readme)
        self.assertIn("--rl-lr-actor 0.0003", readme)
        self.assertIn("--rl-entropy-coeff 0.03", readme)
        self.assertIn("--rl-disable-advantage-normalization", readme)


if __name__ == "__main__":
    unittest.main()
