"""Tests for Chengdu paper-style experiment helpers and script entrypoints."""

from __future__ import annotations

import tempfile
import unittest
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


class PaperExperimentTests(unittest.TestCase):
    """Verify Chengdu paper-style wrappers without running long experiments."""

    def test_run_chengdu_paper_experiment_writes_manifest(self) -> None:
        """One paper-style sweep helper should delegate to the comparison runner and persist a manifest."""
        from experiments.paper_chengdu import run_chengdu_paper_experiment

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            with patch(
                "experiments.paper_chengdu.run_comparison_sweep",
                return_value={"sweep_parameter": "num_parcels", "algorithms": ["capa"], "runs": []},
            ) as run_compare:
                summary = run_chengdu_paper_experiment(
                    axis="num_parcels",
                    output_dir=output_dir,
                    algorithms=("capa", "greedy"),
                    fixed_config_overrides={"data_dir": Path("Data"), "num_parcels": 20},
                    preset_name="smoke",
                    max_workers=2,
                )
            self.assertEqual(summary["sweep_parameter"], "num_parcels")
            self.assertTrue((output_dir / "paper_manifest.json").exists())
            self.assertEqual(run_compare.call_args.kwargs["algorithms"], ("capa", "greedy"))
            self.assertEqual(run_compare.call_args.kwargs["max_workers"], 2)

    def test_run_chengdu_default_comparison_writes_summary_and_plots(self) -> None:
        """The default-setting helper should clone one seeded environment across all algorithms."""
        from env.chengdu import ChengduEnvironment
        from experiments.paper_chengdu import run_chengdu_default_comparison

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

        class FakeRunner:
            """Return a normalized algorithm summary for plotting tests."""

            def __init__(self, name: str) -> None:
                """Store the algorithm name used in the summary."""
                self._name = name

            def run(self, environment: ChengduEnvironment, output_dir: Path | None = None) -> dict[str, object]:
                """Return a normalized result for the default-setting comparison."""
                return {
                    "algorithm": self._name,
                    "metrics": {"TR": 1.0, "CR": 0.5, "BPT": 0.1},
                }

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            with patch("experiments.paper_chengdu.ChengduEnvironment.build", return_value=fake_environment):
                with patch("experiments.paper_chengdu.build_algorithm_runner", side_effect=lambda name, **kwargs: FakeRunner(name)):
                    summary = run_chengdu_default_comparison(
                        output_dir=output_dir,
                        algorithms=("capa", "greedy"),
                        fixed_config_overrides={"data_dir": Path("Data")},
                    )

            self.assertEqual(summary["algorithms"], ["capa", "greedy"])
            self.assertTrue((output_dir / "summary.json").exists())
            self.assertTrue((output_dir / "default_tr_comparison.png").exists())
            self.assertTrue((output_dir / "default_cr_comparison.png").exists())
            self.assertTrue((output_dir / "default_bpt_comparison.png").exists())

    def test_exp1_script_forwards_algorithms_and_workers(self) -> None:
        """The parcel-count script should pass CLI overrides into the shared experiment helper."""
        from experiments.run_chengdu_exp1_num_parcels import main

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch(
                "experiments.run_chengdu_exp1_num_parcels.run_chengdu_paper_experiment",
                return_value={"sweep_parameter": "num_parcels"},
            ) as run_experiment:
                with patch(
                    "sys.argv",
                    [
                        "run_chengdu_exp1_num_parcels.py",
                        "--output-dir",
                        tmpdir,
                        "--preset",
                        "smoke",
                        "--algorithms",
                        "capa",
                        "greedy",
                        "--max-workers",
                        "2",
                    ],
                ):
                    exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(run_experiment.call_args.kwargs["algorithms"], ["capa", "greedy"])
        self.assertEqual(run_experiment.call_args.kwargs["max_workers"], 2)

    def test_suite_script_forwards_algorithms_and_workers(self) -> None:
        """The suite script should pass CLI overrides into the suite helper."""
        from experiments.run_chengdu_paper_suite import main

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch(
                "experiments.run_chengdu_paper_suite.run_chengdu_paper_suite",
                return_value={"suite": "chengdu-paper"},
            ) as run_suite:
                with patch(
                    "sys.argv",
                    [
                        "run_chengdu_paper_suite.py",
                        "--output-dir",
                        tmpdir,
                        "--preset",
                        "smoke",
                        "--algorithms",
                        "capa",
                        "basegta",
                        "--max-workers",
                        "3",
                    ],
                ):
                    exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(run_suite.call_args.kwargs["algorithms"], ["capa", "basegta"])
        self.assertEqual(run_suite.call_args.kwargs["max_workers"], 3)

    def test_run_managed_exp1_retries_then_promotes_successful_round(self) -> None:
        """The managed Exp-1 controller should retry poor CAPA rounds and promote the accepted round."""
        from experiments.run_exp1_managed import run_managed_exp1

        poor_summary = {
            "sweep_parameter": "num_parcels",
            "algorithms": ["capa", "greedy", "basegta"],
            "runs": [
                {
                    "num_parcels": 1000,
                    "capa": {"metrics": {"TR": 50.0, "CR": 0.40, "BPT": 1.0}},
                    "greedy": {"metrics": {"TR": 80.0, "CR": 0.45, "BPT": 0.5}},
                    "basegta": {"metrics": {"TR": 100.0, "CR": 0.50, "BPT": 0.6}},
                }
            ],
        }
        good_summary = {
            "sweep_parameter": "num_parcels",
            "algorithms": ["capa", "greedy", "basegta"],
            "runs": [
                {
                    "num_parcels": 1000,
                    "capa": {"metrics": {"TR": 96.0, "CR": 0.49, "BPT": 1.2}},
                    "greedy": {"metrics": {"TR": 80.0, "CR": 0.45, "BPT": 0.5}},
                    "basegta": {"metrics": {"TR": 100.0, "CR": 0.50, "BPT": 0.6}},
                }
            ],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir) / "tmp"
            final_output_dir = Path(tmpdir) / "final"
            def fake_compare(**kwargs):
                output_dir = kwargs["output_dir"]
                output_dir.mkdir(parents=True, exist_ok=True)
                summary = poor_summary if not (tmp_root / "round_01_paper-default" / "summary.json").exists() else good_summary
                with (output_dir / "summary.json").open("w", encoding="utf-8") as handle:
                    json.dump(summary, handle, indent=2)
                return summary
            with patch(
                "experiments.run_exp1_managed.run_comparison_sweep",
                side_effect=fake_compare,
            ) as run_compare:
                manifest = run_managed_exp1(
                    tmp_root=tmp_root,
                    final_output_dir=final_output_dir,
                    algorithms=("capa", "greedy", "basegta"),
                    preset_name="smoke",
                    max_workers=2,
                    batch_size=30,
                )
                self.assertTrue(manifest["accepted"])
                self.assertEqual(manifest["selected_round"]["round_index"], 2)
                self.assertTrue((tmp_root / "status.json").exists())
                self.assertTrue((tmp_root / "final_manifest.json").exists())
                self.assertTrue((final_output_dir / "summary.json").exists())
                self.assertEqual(run_compare.call_count, 2)
                first_builder = run_compare.call_args_list[0].kwargs["runner_builder"]
                second_builder = run_compare.call_args_list[1].kwargs["runner_builder"]
                self.assertIsNotNone(first_builder)
                self.assertIsNotNone(second_builder)

    def test_managed_exp1_script_forwards_runtime_arguments(self) -> None:
        """The managed Exp-1 script should forward CLI arguments into the controller."""
        from experiments.run_exp1_managed import main

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch(
                "experiments.run_exp1_managed.run_managed_exp1",
                return_value={"accepted": True},
            ) as run_managed:
                with patch(
                    "sys.argv",
                    [
                        "run_exp1_managed.py",
                        "--tmp-root",
                        f"{tmpdir}/tmp",
                        "--final-output-dir",
                        f"{tmpdir}/final",
                        "--preset",
                        "smoke",
                        "--algorithms",
                        "capa",
                        "greedy",
                        "--max-workers",
                        "3",
                        "--batch-size",
                        "30",
                    ],
                ):
                    exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(run_managed.call_args.kwargs["algorithms"], ["capa", "greedy"])
        self.assertEqual(run_managed.call_args.kwargs["max_workers"], 3)
        self.assertEqual(run_managed.call_args.kwargs["batch_size"], 30)

    def test_run_exp1_point_uses_shared_seed_bundle(self) -> None:
        """One Exp-1 point should run algorithms from a shared canonical seed bundle."""
        from env.chengdu import ChengduEnvironment
        from experiments.run_exp1_point import run_exp1_point
        from experiments.seeding import build_environment_seed, save_environment_seed

        environment = ChengduEnvironment(
            tasks=[
                SimpleNamespace(num="t1", s_time=0.0, d_time=10.0),
                SimpleNamespace(num="t2", s_time=1.0, d_time=11.0),
                SimpleNamespace(num="t3", s_time=2.0, d_time=12.0),
            ],
            local_couriers=[SimpleNamespace(num=1)],
            partner_couriers_by_platform={"P1": [SimpleNamespace(num=2)]},
            station_set=[SimpleNamespace(num=1, courier_set=[], f_pick_task_set=[])],
            travel_model=object(),
            platform_base_prices={"P1": 1.0},
            platform_sharing_rates={"P1": 0.4},
            platform_qualities={"P1": 0.9},
        )

        class FakeRunner:
            """Return a normalized point summary while exposing task counts."""

            def __init__(self, name: str) -> None:
                self._name = name

            def run(self, environment, output_dir=None) -> dict[str, object]:
                return {
                    "algorithm": self._name,
                    "metrics": {
                        "TR": float(len(environment.tasks)),
                        "CR": 1.0,
                        "BPT": 0.1,
                    },
                }

        with tempfile.TemporaryDirectory() as tmpdir:
            seed_path = Path(tmpdir) / "seed.pkl"
            save_environment_seed(build_environment_seed(environment), seed_path)
            with patch("experiments.run_exp1_point.load_environment_seed", return_value=build_environment_seed(environment)):
                with patch("experiments.run_exp1_point.build_algorithm_runner", side_effect=lambda name, **kwargs: FakeRunner(name)):
                    summary = run_exp1_point(
                        seed_path=seed_path,
                        num_parcels=2,
                        output_dir=Path(tmpdir) / "point",
                        algorithms=("capa", "greedy"),
                        batch_size=30,
                    )

        self.assertEqual(summary["num_parcels"], 2)
        self.assertEqual(summary["capa"]["metrics"]["TR"], 2.0)

    def test_run_exp1_split_aggregates_completed_points(self) -> None:
        """The split Exp-1 launcher should aggregate point summaries after every point finishes."""
        from experiments.run_exp1_split import run_exp1_split

        class FakeProcess:
            """Represent one already-finished point process."""

            _next_pid = 1000

            def __init__(self, *args, **kwargs) -> None:
                self.pid = FakeProcess._next_pid
                FakeProcess._next_pid += 1
                self.returncode = 0

            def poll(self) -> int:
                return self.returncode

        class FakeRunnerBuilder:
            """Placeholder used only to keep patch scopes explicit."""

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir) / "tmp"
            output_dir = Path(tmpdir) / "out"
            point_summaries = {
                1000: {"num_parcels": 1000, "capa": {"metrics": {"TR": 10.0, "CR": 0.5, "BPT": 1.0}}},
                2000: {"num_parcels": 2000, "capa": {"metrics": {"TR": 20.0, "CR": 0.6, "BPT": 1.5}}},
            }

            def fake_popen(cmd, cwd=None, stdout=None, stderr=None, text=None):
                point_value = int(cmd[cmd.index("--num-parcels") + 1])
                output_path = Path(cmd[cmd.index("--output-dir") + 1])
                output_path.mkdir(parents=True, exist_ok=True)
                with (output_path / "summary.json").open("w", encoding="utf-8") as handle:
                    json.dump(point_summaries[point_value], handle, indent=2)
                return FakeProcess()

            fake_environment = SimpleNamespace()

            with patch("experiments.run_exp1_split.ChengduEnvironment.build", return_value=fake_environment):
                with patch("experiments.run_exp1_split.build_environment_seed", return_value="seed-object"):
                    with patch("experiments.run_exp1_split.save_environment_seed") as save_seed:
                        with patch("experiments.run_exp1_split.subprocess.Popen", side_effect=fake_popen):
                            with patch("experiments.run_exp1_split.save_comparison_plots") as save_plots:
                                summary = run_exp1_split(
                                    tmp_root=tmp_root,
                                    output_dir=output_dir,
                                    algorithms=("capa",),
                                    parcel_values=(1000, 2000),
                                    batch_size=30,
                                    poll_seconds=0,
                                )

            self.assertEqual([run["num_parcels"] for run in summary["runs"]], [1000, 2000])
            self.assertTrue((output_dir / "summary.json").exists())
            self.assertTrue((output_dir / "split_manifest.json").exists())
            self.assertTrue(save_seed.called)
            self.assertTrue(save_plots.called)


if __name__ == "__main__":
    unittest.main()
