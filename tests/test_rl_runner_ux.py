"""Focused RL-CAPA runner UX regression tests."""

from __future__ import annotations

import unittest

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


if __name__ == "__main__":
    unittest.main()
