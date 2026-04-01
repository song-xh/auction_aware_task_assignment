"""Tests for predefined experiment suites and axis validation."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path


class ExperimentSuiteTests(unittest.TestCase):
    """Validate experiment suite orchestration and explicit axis handling."""

    def test_suite_runs_multiple_predefined_comparisons(self) -> None:
        """The paper-main suite should expand into multiple comparison runs and persist a manifest."""
        from experiments.suites import run_experiment_suite

        compare_calls: list[tuple[str, tuple[int, ...]]] = []

        def fake_compare(**kwargs):
            compare_calls.append((kwargs["sweep_parameter"], tuple(kwargs["sweep_values"])))
            return {
                "sweep_parameter": kwargs["sweep_parameter"],
                "algorithms": list(kwargs["algorithms"]),
                "runs": [],
            }

        with tempfile.TemporaryDirectory() as tmpdir:
            summary = run_experiment_suite(
                suite_name="paper-main",
                preset_name="chengdu-formal",
                algorithms=["capa", "greedy"],
                output_dir=Path(tmpdir),
                fixed_config={
                    "data_dir": Path("Data"),
                    "num_parcels": 20,
                    "local_couriers": 2,
                    "platforms": 1,
                    "couriers_per_platform": 1,
                    "batch_size": 300,
                },
                comparison_runner=fake_compare,
            )

        self.assertEqual(summary["suite"], "paper-main")
        self.assertEqual(summary["preset"], "chengdu-formal")
        self.assertEqual(
            compare_calls,
            [
                ("num_parcels", (100, 200, 500)),
                ("local_couriers", (10, 20, 30)),
                ("platforms", (1, 2, 4)),
                ("batch_size", (60, 300, 600)),
            ],
        )

    def test_suite_smoke_preset_uses_smaller_axis_values(self) -> None:
        """The smoke preset should map to the reduced quick-run axis grid."""
        from experiments.suites import run_experiment_suite

        compare_calls: list[tuple[str, tuple[int, ...]]] = []

        def fake_compare(**kwargs):
            compare_calls.append((kwargs["sweep_parameter"], tuple(kwargs["sweep_values"])))
            return {
                "sweep_parameter": kwargs["sweep_parameter"],
                "algorithms": list(kwargs["algorithms"]),
                "runs": [],
            }

        with tempfile.TemporaryDirectory() as tmpdir:
            summary = run_experiment_suite(
                suite_name="paper-main",
                preset_name="smoke",
                algorithms=["capa", "greedy"],
                output_dir=Path(tmpdir),
                fixed_config={
                    "data_dir": Path("Data"),
                    "num_parcels": 20,
                    "local_couriers": 2,
                    "platforms": 1,
                    "couriers_per_platform": 1,
                    "batch_size": 300,
                },
                comparison_runner=fake_compare,
            )

        self.assertEqual(summary["preset"], "smoke")
        self.assertEqual(
            compare_calls,
            [
                ("num_parcels", (20, 50)),
                ("local_couriers", (2, 4)),
                ("platforms", (1, 2)),
                ("batch_size", (60, 300)),
            ],
        )

    def test_sweep_axis_validation_fails_explicitly_for_unsupported_service_radius(self) -> None:
        """Unsupported axes such as service radius should fail explicitly until the environment exposes them."""
        from experiments.sweep import run_parameter_sweep

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaisesRegex(NotImplementedError, "service_radius"):
                run_parameter_sweep(
                    algorithm="capa",
                    output_dir=Path(tmpdir),
                    sweep_parameter="service_radius",
                    sweep_values=[1000, 2000],
                    fixed_config={
                        "data_dir": Path("Data"),
                        "num_parcels": 20,
                        "local_couriers": 2,
                        "platforms": 1,
                        "couriers_per_platform": 1,
                        "batch_size": 300,
                    },
                )


if __name__ == "__main__":
    unittest.main()
