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

    def test_rl_capa_registration_is_explicitly_unimplemented(self) -> None:
        """The rl-capa registry entry should exist but fail explicitly when invoked."""
        from algorithms.registry import build_algorithm_runner

        runner = build_algorithm_runner("rl-capa")
        with self.assertRaises(NotImplementedError):
            runner.run(environment=None, output_dir=None)


if __name__ == "__main__":
    unittest.main()
