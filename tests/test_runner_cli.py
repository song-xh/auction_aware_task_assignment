"""Tests for the unified root-runner strategy dispatch layer."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from capa import DistanceMatrixTravelModel
from env.chengdu import ChengduEnvironment
from tests.test_chengdu_runner import FakeLegacyCourier, FakeStation, FakeTask


class RunnerDispatchTests(unittest.TestCase):
    """Validate algorithm dispatch before the root CLI is added."""

    def test_capa_strategy_runs_against_unified_environment(self) -> None:
        """The CAPA strategy wrapper should run against the unified Chengdu environment."""
        from algorithms.registry import build_algorithm_runner

        travel = DistanceMatrixTravelModel(
            distances={
                ("L0", "T1"): 2.0,
                ("L0", "S"): 4.0,
                ("T1", "S"): 2.0,
                ("P0", "PS"): 4.0,
                ("P0", "T1"): 8.0,
                ("T1", "PS"): 6.0,
            },
            speed=1.0,
        )
        local_station = FakeStation(1, "S")
        partner_station = FakeStation(2, "PS")
        environment = ChengduEnvironment(
            tasks=[FakeTask("t1", "T1", 0, 30, 1.0, 10.0)],
            local_couriers=[FakeLegacyCourier(num=1, location="L0", station=local_station)],
            partner_couriers_by_platform={"P1": [FakeLegacyCourier(num=2, location="P0", station=partner_station)]},
            station_set=[local_station, partner_station],
            travel_model=travel,
            platform_base_prices={"P1": 1.0},
            platform_sharing_rates={"P1": 0.4},
            platform_qualities={"P1": 1.0},
            movement_callback=lambda local, partner, step, station_set: [
                courier.re_schedule.pop(0)
                for courier in [*local, *partner]
                if getattr(courier, "re_schedule", [])
            ],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            runner = build_algorithm_runner("capa", batch_size=60)
            result = runner.run(environment=environment, output_dir=Path(tmpdir))

        self.assertEqual(result["algorithm"], "capa")
        self.assertIn("metrics", result)
        self.assertIn("TR", result["metrics"])

    def test_all_baselines_share_same_environment_contract(self) -> None:
        """Greedy, BaseGTA, and ImpGTA should all dispatch through the same runner interface."""
        from algorithms.registry import build_algorithm_runner

        environment = ChengduEnvironment(
            tasks=[],
            local_couriers=[],
            partner_couriers_by_platform={},
            station_set=[],
            travel_model=None,
            platform_base_prices={},
            platform_sharing_rates={},
            platform_qualities={},
        )

        def fake_baseline_runner(**kwargs):
            return {
                "TR": 1.0,
                "CR": 0.5,
                "BPT": 0.1,
                "delivered_parcels": 1,
                "accepted_assignments": 1,
            }

        for name in ["greedy", "basegta", "impgta"]:
            runner = build_algorithm_runner(name, baseline_runner=fake_baseline_runner)
            result = runner.run(environment=environment, output_dir=None)
            self.assertEqual(result["algorithm"], name)
            self.assertEqual(result["metrics"]["TR"], 1.0)

    def test_root_runner_dispatches_selected_algorithm(self) -> None:
        """The root runner should build the environment once and dispatch the selected algorithm."""
        from runner import main

        fake_environment = ChengduEnvironment(
            tasks=[],
            local_couriers=[],
            partner_couriers_by_platform={},
            station_set=[],
            travel_model=None,
            platform_base_prices={},
            platform_sharing_rates={},
            platform_qualities={},
        )

        class FakeAlgorithmRunner:
            """Record the environment passed in and return a normalized summary."""

            def run(self, environment, output_dir=None):
                self.environment = environment
                self.output_dir = output_dir
                return {
                    "algorithm": "capa",
                    "metrics": {
                        "TR": 1.0,
                        "CR": 0.5,
                        "BPT": 0.1,
                    },
                }

        with tempfile.TemporaryDirectory() as tmpdir:
            fake_runner = FakeAlgorithmRunner()
            with patch("runner.ChengduEnvironment.build", return_value=fake_environment) as build_environment:
                with patch("runner.build_algorithm_runner", return_value=fake_runner) as build_runner:
                    exit_code = main(
                        [
                            "--algorithm",
                            "capa",
                            "--data-dir",
                            "Data",
                            "--num-parcels",
                            "10",
                            "--local-couriers",
                            "2",
                            "--platforms",
                            "1",
                            "--couriers-per-platform",
                            "1",
                            "--batch-size",
                            "300",
                            "--output-dir",
                            tmpdir,
                        ]
                    )

        self.assertEqual(exit_code, 0)
        build_environment.assert_called_once()
        build_runner.assert_called_once()
        self.assertIs(fake_runner.environment, fake_environment)
        self.assertEqual(Path(fake_runner.output_dir), Path(tmpdir))

    def test_root_runner_compare_subcommand_delegates_to_experiment_orchestrator(self) -> None:
        """The root runner compare mode should delegate to the shared-environment comparison orchestrator."""
        from runner import main

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("runner.run_comparison_sweep", return_value={"runs": []}) as run_compare:
                exit_code = main(
                    [
                        "compare",
                        "--algorithms",
                        "capa",
                        "greedy",
                        "--axis",
                        "num_parcels",
                        "--values",
                        "10",
                        "20",
                        "--data-dir",
                        "Data",
                        "--local-couriers",
                        "2",
                        "--platforms",
                        "1",
                        "--couriers-per-platform",
                        "1",
                        "--batch-size",
                        "300",
                        "--output-dir",
                        tmpdir,
                    ]
                )

        self.assertEqual(exit_code, 0)
        run_compare.assert_called_once()

    def test_root_runner_sweep_subcommand_passes_max_workers(self) -> None:
        """The root runner sweep mode should forward optional process-count configuration."""
        from runner import main

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("runner.run_parameter_sweep", return_value={"algorithm": "capa", "sweep_parameter": "num_parcels"}) as run_sweep:
                exit_code = main(
                    [
                        "sweep",
                        "--algorithm",
                        "capa",
                        "--axis",
                        "num_parcels",
                        "--values",
                        "10",
                        "20",
                        "--data-dir",
                        "Data",
                        "--max-workers",
                        "3",
                        "--output-dir",
                        tmpdir,
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(run_sweep.call_args.kwargs["max_workers"], 3)

    def test_root_runner_suite_subcommand_delegates_to_suite_orchestrator(self) -> None:
        """The root runner suite mode should delegate to the predefined experiment-suite orchestrator."""
        from runner import main

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("runner.run_experiment_suite", return_value={"suite": "chengdu-paper", "preset": "formal"}) as run_suite:
                exit_code = main(
                    [
                        "suite",
                        "--suite",
                        "chengdu-paper",
                        "--preset",
                        "formal",
                        "--algorithms",
                        "capa",
                        "greedy",
                        "--data-dir",
                        "Data",
                        "--local-couriers",
                        "2",
                        "--platforms",
                        "1",
                        "--couriers-per-platform",
                        "1",
                        "--batch-size",
                        "300",
                        "--max-workers",
                        "4",
                        "--output-dir",
                        tmpdir,
                    ]
                )

        self.assertEqual(exit_code, 0)
        run_suite.assert_called_once()
        self.assertEqual(run_suite.call_args.kwargs["max_workers"], 4)

    def test_root_runner_accepts_legacy_single_run_flags_without_subcommand(self) -> None:
        """The root runner should keep legacy single-run flags working by treating them as `run`."""
        from runner import main

        fake_environment = ChengduEnvironment(
            tasks=[],
            local_couriers=[],
            partner_couriers_by_platform={},
            station_set=[],
            travel_model=None,
            platform_base_prices={},
            platform_sharing_rates={},
            platform_qualities={},
        )

        class FakeAlgorithmRunner:
            """Record the environment passed in and return a normalized summary."""

            def run(self, environment, output_dir=None):
                self.environment = environment
                self.output_dir = output_dir
                return {
                    "algorithm": "capa",
                    "metrics": {
                        "TR": 1.0,
                        "CR": 0.5,
                        "BPT": 0.1,
                    },
                }

        with tempfile.TemporaryDirectory() as tmpdir:
            fake_runner = FakeAlgorithmRunner()
            with patch("runner.ChengduEnvironment.build", return_value=fake_environment):
                with patch("runner.build_algorithm_runner", return_value=fake_runner):
                    exit_code = main(
                        [
                            "--algorithm",
                            "capa",
                            "--data-dir",
                            "Data",
                            "--output-dir",
                            tmpdir,
                        ]
                    )

        self.assertEqual(exit_code, 0)
        self.assertIs(fake_runner.environment, fake_environment)

    def test_parse_args_uses_sys_argv_when_none(self) -> None:
        """The root runner parser should honor the real CLI argv when no explicit argv is passed."""
        from runner import parse_args

        with patch("sys.argv", ["runner.py", "compare", "--algorithms", "capa", "greedy", "--axis", "num_parcels", "--values", "5"]):
            args = parse_args(None)

        self.assertEqual(args.command, "compare")
        self.assertEqual(args.algorithms, ["capa", "greedy"])

    def test_rl_capa_cli_dispatches_through_unified_runner(self) -> None:
        """Selecting rl-capa should run through the unified registry without fallback."""
        from runner import main

        fake_environment = ChengduEnvironment(
            tasks=[],
            local_couriers=[],
            partner_couriers_by_platform={},
            station_set=[],
            travel_model=None,
            platform_base_prices={},
            platform_sharing_rates={},
            platform_qualities={},
        )

        class FakeAlgorithmRunner:
            """Record the environment passed in and return a normalized summary."""

            def run(self, environment, output_dir=None):
                self.environment = environment
                self.output_dir = output_dir
                return {
                    "algorithm": "rl-capa",
                    "metrics": {
                        "TR": 1.0,
                        "CR": 1.0,
                        "BPT": 0.1,
                    },
                }

        with patch("runner.ChengduEnvironment.build", return_value=fake_environment):
            with patch("runner.build_algorithm_runner", return_value=FakeAlgorithmRunner()):
                exit_code = main(
                    [
                        "--algorithm",
                        "rl-capa",
                        "--data-dir",
                        "Data",
                        "--output-dir",
                        "outputs/plots/test_rl_capa_cli",
                    ]
                )

        self.assertEqual(exit_code, 0)

    def test_root_runner_is_the_documented_primary_entrypoint(self) -> None:
        """The README should present the root runner as the canonical way to launch experiments."""
        readme = Path("README.md").read_text(encoding="utf-8")

        self.assertIn("python3 runner.py run --algorithm capa", readme)
        self.assertIn("python3 runner.py sweep", readme)
        self.assertIn("python3 runner.py compare", readme)
        self.assertIn("python3 runner.py suite", readme)


if __name__ == "__main__":
    unittest.main()
