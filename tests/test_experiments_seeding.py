"""Tests for shared-environment experiment seeding and cloning."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

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
            geo_index={"A": (30.0, 104.0)},
            travel_speed_m_per_s=11.0,
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
        self.assertEqual(clone_a.geo_index, clone_b.geo_index)
        self.assertEqual(clone_a.travel_speed_m_per_s, 11.0)

    def test_persisted_seed_reconstructs_shared_couriers_and_task_prefixes(self) -> None:
        """Persisted canonical seeds should rebuild identical courier/station state across parcel-count points."""
        from experiments.seeding import (
            build_environment_seed,
            derive_environment_from_seed,
            load_environment_seed,
            save_environment_seed,
        )

        station = {"station_id": "s1", "num": "s1", "courier_set": [], "f_pick_task_set": []}
        local_courier = {"courier_id": "c1", "station": station, "station_num": "s1", "route": []}
        tasks = [
            {"task_id": "t1", "num": "t1", "s_time": 0.0, "d_time": 10.0},
            {"task_id": "t2", "num": "t2", "s_time": 1.0, "d_time": 11.0},
            {"task_id": "t3", "num": "t3", "s_time": 2.0, "d_time": 12.0},
        ]
        station["courier_set"].append(local_courier)
        station["f_pick_task_set"].extend(tasks)
        environment = ChengduEnvironment(
            tasks=tasks,
            local_couriers=[local_courier],
            partner_couriers_by_platform={"P1": []},
            station_set=[station],
            travel_model=object(),
            platform_base_prices={"P1": 1.0},
            platform_sharing_rates={"P1": 0.4},
            platform_qualities={"P1": 0.9},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            seed_path = Path(tmpdir) / "seed.pkl"
            save_environment_seed(build_environment_seed(environment), seed_path)
            loaded_seed = load_environment_seed(seed_path, travel_model_factory=object, movement_callback=None)
            env_small = derive_environment_from_seed(loaded_seed, num_parcels=2)
            env_large = derive_environment_from_seed(loaded_seed, num_parcels=3)

        self.assertEqual([task["task_id"] for task in env_small.tasks], ["t1", "t2"])
        self.assertEqual([task["task_id"] for task in env_large.tasks], ["t1", "t2", "t3"])
        self.assertEqual(env_small.local_couriers[0]["courier_id"], env_large.local_couriers[0]["courier_id"])
        self.assertEqual(env_small.station_set[0]["station_id"], env_large.station_set[0]["station_id"])
        self.assertEqual([task["task_id"] for task in env_small.station_set[0]["f_pick_task_set"]], ["t1", "t2"])

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

    def test_parameter_sweep_parallelizes_points_when_requested(self) -> None:
        """Single-algorithm sweeps should fan out sweep points when process parallelism is requested."""
        from experiments.sweep import run_parameter_sweep

        submitted: list[float] = []

        class FakeFuture:
            """Return a precomputed sweep entry when resolved."""

            def __init__(self, value: dict[str, object]) -> None:
                """Store the synthetic future payload."""
                self._value = value

            def result(self) -> dict[str, object]:
                """Return the stored sweep entry."""
                return self._value

        class FakeExecutor:
            """Capture submitted sweep jobs without spawning worker processes."""

            def __init__(self, max_workers: int) -> None:
                """Store the configured process count for completeness."""
                self.max_workers = max_workers

            def __enter__(self) -> "FakeExecutor":
                """Return the executor context manager instance."""
                return self

            def __exit__(self, exc_type, exc, tb) -> None:
                """Close the fake executor context without extra work."""
                return None

            def submit(self, fn, **kwargs) -> FakeFuture:
                """Record the requested sweep point and execute it immediately."""
                submitted.append(kwargs["value"])
                return FakeFuture(fn(**kwargs))

        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch("experiments.sweep.ProcessPoolExecutor", FakeExecutor):
                with mock.patch(
                    "experiments.sweep._run_sweep_point",
                    side_effect=lambda **kwargs: {
                        "num_parcels": kwargs["value"],
                        "capa": {"metrics": {"TR": kwargs["value"], "CR": 1.0, "BPT": 0.1}},
                    },
                ):
                    summary = run_parameter_sweep(
                        algorithm="capa",
                        output_dir=Path(tmpdir),
                        sweep_parameter="num_parcels",
                        sweep_values=[20, 10],
                        fixed_config={
                            "data_dir": Path("Data"),
                            "num_parcels": 5,
                            "local_couriers": 2,
                            "platforms": 1,
                            "couriers_per_platform": 1,
                            "batch_size": 300,
                        },
                        max_workers=2,
                    )

        self.assertEqual(submitted, [20, 10])
        self.assertEqual([run["num_parcels"] for run in summary["runs"]], [10, 20])

    def test_courier_capacity_sweep_maps_into_environment_config(self) -> None:
        """Courier-capacity sweeps should forward capacity values into the unified environment builder."""
        from experiments.sweep import run_parameter_sweep

        build_calls: list[float] = []

        def build_environment(**kwargs) -> ChengduEnvironment:
            build_calls.append(kwargs["courier_capacity"])
            return ChengduEnvironment(
                tasks=[],
                local_couriers=[],
                partner_couriers_by_platform={},
                station_set=[],
                travel_model=None,
                platform_base_prices={},
                platform_sharing_rates={},
                platform_qualities={},
                courier_capacity=kwargs["courier_capacity"],
            )

        class FakeRunner:
            """Return a normalized summary for courier-capacity sweeps."""

            def run(self, environment: ChengduEnvironment, output_dir: Path | None = None) -> dict[str, object]:
                return {
                    "algorithm": "capa",
                    "metrics": {
                        "TR": 1.0,
                        "CR": 0.5,
                        "BPT": 0.1,
                    },
                }

        with tempfile.TemporaryDirectory() as tmpdir:
            run_parameter_sweep(
                algorithm="capa",
                output_dir=Path(tmpdir),
                sweep_parameter="courier_capacity",
                sweep_values=[25, 50],
                fixed_config={
                    "data_dir": Path("Data"),
                    "num_parcels": 20,
                    "local_couriers": 2,
                    "platforms": 1,
                    "couriers_per_platform": 1,
                    "batch_size": 300,
                },
                environment_builder=build_environment,
                runner_builder=lambda name, **kwargs: FakeRunner(),
            )

        self.assertEqual(build_calls, [25, 50])

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
