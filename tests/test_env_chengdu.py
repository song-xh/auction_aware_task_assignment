"""Tests for the reusable Chengdu environment package."""

import subprocess
import unittest


class EnvChengduTests(unittest.TestCase):
    """Validate the environment-layer interfaces extracted from CAPA."""

    def test_environment_object_keeps_local_and_partner_couriers_separate(self) -> None:
        """The reusable environment facade should expose local and partner courier pools separately."""
        from env.chengdu import LegacyChengduEnvironment

        environment = LegacyChengduEnvironment(
            tasks=[],
            local_couriers=["local-1", "local-2"],
            partner_couriers_by_platform={"P1": ["partner-1"], "P2": ["partner-2", "partner-3"]},
            station_set=[],
            travel_model=None,
            platform_base_prices={"P1": 1.0, "P2": 1.0},
            platform_sharing_rates={"P1": 0.4, "P2": 0.4},
            platform_qualities={"P1": 1.0, "P2": 0.9},
        )

        self.assertEqual(environment.local_couriers, ["local-1", "local-2"])
        self.assertEqual(environment.partner_couriers_by_platform["P1"], ["partner-1"])
        self.assertEqual(environment.all_partner_couriers(), ["partner-1", "partner-2", "partner-3"])

    def test_env_chengdu_imports_without_circular_dependency(self) -> None:
        """The standalone environment package should import cleanly in a fresh interpreter."""
        result = subprocess.run(
            ["python3", "-c", "import env.chengdu; print('ok')"],
            cwd="/root/code/auction_aware_task_assignment",
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("ok", result.stdout)


if __name__ == "__main__":
    unittest.main()
