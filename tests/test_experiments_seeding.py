"""Tests for shared-environment experiment seeding and cloning."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from env.chengdu import ChengduEnvironment


class ExperimentsSeedingTests(unittest.TestCase):
    """Validate same-environment guarantees for experiment comparisons."""

    def test_environment_seed_clones_share_initial_state_but_not_mutations(self) -> None:
        """Cloned environments should start identical while remaining independently mutable."""
        from experiments.seeding import build_environment_seed, clone_environment_from_seed

        station = {"station_id": "s1", "courier_set": [], "f_pick_task_set": []}
        local_courier = {"courier_id": "c1", "route": ["A"], "station": station, "station_num": "s1"}
        task = {"task_id": "t1"}
        station["courier_set"].append(local_courier)
        station["f_pick_task_set"].append(task)
        environment = ChengduEnvironment(
            tasks=[task],
            local_couriers=[local_courier],
            partner_couriers_by_platform={"P1": [{"courier_id": "p1", "route": ["B"]}]},
            station_set=[station],
            travel_model=object(),
            platform_base_prices={"P1": 1.0},
            platform_sharing_rates={"P1": 0.4},
            platform_qualities={"P1": 0.9},
        )

        seed = build_environment_seed(environment)
        clone_a = clone_environment_from_seed(seed)
        clone_b = clone_environment_from_seed(seed)

        self.assertEqual(clone_a.tasks[0]["task_id"], clone_b.tasks[0]["task_id"])
        self.assertEqual(clone_a.local_couriers[0]["courier_id"], clone_b.local_couriers[0]["courier_id"])
        self.assertIs(clone_a.travel_model, clone_b.travel_model)

        clone_a.tasks.append({"task_id": "t2"})
        clone_a.local_couriers[0]["route"].append("C")

        self.assertEqual(len(clone_b.tasks), 1)
        self.assertEqual(clone_b.local_couriers[0]["route"], ["A"])
        self.assertIs(clone_a.local_couriers[0]["station"], clone_a.station_set[0])
        self.assertIs(clone_b.local_couriers[0]["station"], clone_b.station_set[0])
        self.assertIs(clone_a.station_set[0]["courier_set"][0], clone_a.local_couriers[0])
        self.assertIs(clone_b.station_set[0]["courier_set"][0], clone_b.local_couriers[0])
        self.assertIs(clone_a.station_set[0]["f_pick_task_set"][0], clone_a.tasks[0])
        self.assertIs(clone_b.station_set[0]["f_pick_task_set"][0], clone_b.tasks[0])

    def test_compare_runner_reuses_one_seeded_environment_per_sweep_value(self) -> None:
        """Comparison sweeps should build once per sweep point, then clone for each algorithm run."""
        from experiments.compare import run_comparison_sweep

        build_calls: list[int] = []
        algorithm_environment_ids: list[tuple[str, int]] = []

        def build_environment(**kwargs) -> ChengduEnvironment:
            build_calls.append(kwargs["num_parcels"])
            return ChengduEnvironment(
                tasks=[{"task_id": f"t{kwargs['num_parcels']}"}],
                local_couriers=[{"courier_id": "c1"}],
                partner_couriers_by_platform={"P1": [{"courier_id": "p1"}]},
                station_set=[{"station_id": "s1"}],
                travel_model=object(),
                platform_base_prices={"P1": 1.0},
                platform_sharing_rates={"P1": 0.4},
                platform_qualities={"P1": 0.9},
            )

        class FakeRunner:
            """Record the environment identity used for each algorithm execution."""

            def __init__(self, name: str) -> None:
                """Store the algorithm name used in the normalized summary."""
                self._name = name

            def run(self, environment: ChengduEnvironment, output_dir: Path | None = None) -> dict[str, object]:
                """Return a normalized summary while recording the provided environment identity."""
                algorithm_environment_ids.append((self._name, id(environment)))
                return {
                    "algorithm": self._name,
                    "metrics": {
                        "TR": 1.0,
                        "CR": 0.5,
                        "BPT": 0.1,
                    },
                }

        def build_runner(name: str, **kwargs) -> FakeRunner:
            """Build a fake algorithm runner for the given comparison test."""
            return FakeRunner(name)

        with tempfile.TemporaryDirectory() as tmpdir:
            summary = run_comparison_sweep(
                algorithms=["capa", "greedy"],
                output_dir=Path(tmpdir),
                sweep_parameter="num_parcels",
                sweep_values=[10, 20],
                fixed_config={
                    "data_dir": Path("Data"),
                    "local_couriers": 2,
                    "platforms": 1,
                    "couriers_per_platform": 1,
                    "batch_size": 300,
                },
                environment_builder=build_environment,
                runner_builder=build_runner,
            )

        self.assertEqual(build_calls, [10, 20])
        self.assertEqual(len(summary["runs"]), 2)
        self.assertEqual(len(algorithm_environment_ids), 4)
        self.assertNotEqual(algorithm_environment_ids[0][1], algorithm_environment_ids[1][1])
        self.assertNotEqual(algorithm_environment_ids[2][1], algorithm_environment_ids[3][1])

    def test_parameter_sweep_maps_axis_into_environment_and_runner_config(self) -> None:
        """Single-algorithm sweeps should vary the requested axis while preserving shared fixed fields."""
        from experiments.sweep import run_parameter_sweep

        build_calls: list[tuple[int, int]] = []
        runner_calls: list[int] = []

        def build_environment(**kwargs) -> ChengduEnvironment:
            build_calls.append((kwargs["num_parcels"], kwargs["local_courier_count"]))
            return ChengduEnvironment(
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
            """Capture the batch size used to create the runner."""

            def __init__(self, batch_size: int = 0) -> None:
                """Store the normalized batch size for later assertions."""
                self._batch_size = batch_size

            def run(self, environment: ChengduEnvironment, output_dir: Path | None = None) -> dict[str, object]:
                """Return a normalized sweep summary."""
                runner_calls.append(self._batch_size)
                return {
                    "algorithm": "capa",
                    "metrics": {
                        "TR": 1.0,
                        "CR": 0.5,
                        "BPT": 0.1,
                    },
                }

        def build_runner(name: str, **kwargs) -> FakeRunner:
            """Build a fake runner so the test can inspect mapped kwargs."""
            return FakeRunner(batch_size=kwargs.get("batch_size", 0))

        with tempfile.TemporaryDirectory() as tmpdir:
            summary = run_parameter_sweep(
                algorithm="capa",
                output_dir=Path(tmpdir),
                sweep_parameter="num_parcels",
                sweep_values=[10, 20],
                fixed_config={
                    "data_dir": Path("Data"),
                    "num_parcels": 5,
                    "local_couriers": 2,
                    "platforms": 1,
                    "couriers_per_platform": 1,
                    "batch_size": 300,
                },
                environment_builder=build_environment,
                runner_builder=build_runner,
            )

        self.assertEqual(summary["algorithm"], "capa")
        self.assertEqual(build_calls, [(10, 2), (20, 2)])
        self.assertEqual(runner_calls, [300, 300])

    def test_service_radius_sweep_maps_into_environment_config(self) -> None:
        """Service-radius sweeps should forward radius values into the unified environment builder."""
        from experiments.sweep import run_parameter_sweep

        build_calls: list[float] = []

        def build_environment(**kwargs) -> ChengduEnvironment:
            build_calls.append(kwargs["service_radius_km"])
            return ChengduEnvironment(
                tasks=[],
                local_couriers=[],
                partner_couriers_by_platform={},
                station_set=[],
                travel_model=None,
                platform_base_prices={},
                platform_sharing_rates={},
                platform_qualities={},
                service_radius_km=kwargs["service_radius_km"],
            )

        class FakeRunner:
            """Return a normalized summary for radius-sweep tests."""

            def run(self, environment: ChengduEnvironment, output_dir: Path | None = None) -> dict[str, object]:
                return {
                    "algorithm": "capa",
                    "metrics": {
                        "TR": 1.0,
                        "CR": 0.5,
                        "BPT": 0.1,
                    },
                }

        def build_runner(name: str, **kwargs) -> FakeRunner:
            """Build a fake runner for the service-radius sweep test."""
            return FakeRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            run_parameter_sweep(
                algorithm="capa",
                output_dir=Path(tmpdir),
                sweep_parameter="service_radius",
                sweep_values=[0.5, 1.5],
                fixed_config={
                    "data_dir": Path("Data"),
                    "num_parcels": 20,
                    "local_couriers": 2,
                    "platforms": 1,
                    "couriers_per_platform": 1,
                    "batch_size": 300,
                },
                environment_builder=build_environment,
                runner_builder=build_runner,
            )

        self.assertEqual(build_calls, [0.5, 1.5])

    def test_compare_runner_kwargs_do_not_pass_batch_size_to_basegta(self) -> None:
        """Shared-environment comparisons should not send unsupported kwargs to BaseGTA runners."""
        from experiments.compare import run_comparison_sweep

        observed_runner_kwargs: list[tuple[str, dict[str, object]]] = []

        def build_environment(**kwargs) -> ChengduEnvironment:
            return ChengduEnvironment(
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
            """Return a normalized summary for compare-kwargs tests."""

            def __init__(self, algorithm_name: str) -> None:
                """Store the algorithm name for the normalized summary."""
                self._algorithm_name = algorithm_name

            def run(self, environment: ChengduEnvironment, output_dir: Path | None = None) -> dict[str, object]:
                """Return a minimal normalized summary."""
                return {
                    "algorithm": self._algorithm_name,
                    "metrics": {
                        "TR": 1.0,
                        "CR": 0.5,
                        "BPT": 0.1,
                    },
                }

        def build_runner(name: str, **kwargs) -> FakeRunner:
            """Record runner kwargs so the test can verify per-algorithm mapping."""
            observed_runner_kwargs.append((name, dict(kwargs)))
            return FakeRunner(name)

        with tempfile.TemporaryDirectory() as tmpdir:
            run_comparison_sweep(
                algorithms=["basegta", "mra"],
                output_dir=Path(tmpdir),
                sweep_parameter="num_parcels",
                sweep_values=[10],
                fixed_config={
                    "data_dir": Path("Data"),
                    "num_parcels": 10,
                    "local_couriers": 2,
                    "platforms": 1,
                    "couriers_per_platform": 1,
                    "batch_size": 300,
                },
                environment_builder=build_environment,
                runner_builder=build_runner,
            )

        self.assertEqual(observed_runner_kwargs[0], ("basegta", {}))
        self.assertEqual(observed_runner_kwargs[1], ("mra", {"batch_size": 300}))


if __name__ == "__main__":
    unittest.main()
