"""Tests for the unified algorithm registry."""

from __future__ import annotations

import unittest


class AlgorithmRegistryTests(unittest.TestCase):
    """Validate the top-level algorithm registry contract."""

    def test_registry_exposes_all_supported_algorithm_names(self) -> None:
        """The registry should publish the canonical algorithm names."""
        from algorithms.registry import get_algorithm_names

        self.assertEqual(
            get_algorithm_names(),
            [
                "basegta",
                "capa",
                "greedy",
                "impgta",
                "mra",
                "ramcom",
                "rl-capa",
            ],
        )

    def test_rl_capa_registration_builds_real_runner(self) -> None:
        """The rl-capa registry entry should resolve to a runnable implementation."""
        from algorithms.registry import build_algorithm_runner

        runner = build_algorithm_runner("rl-capa")
        self.assertTrue(hasattr(runner, "run"))


if __name__ == "__main__":
    unittest.main()
