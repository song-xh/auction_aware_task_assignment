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

        environment = ChengduEnvironment(
            tasks=[{"task_id": "t1"}],
            local_couriers=[{"courier_id": "c1", "route": ["A"]}],
            partner_couriers_by_platform={"P1": [{"courier_id": "p1", "route": ["B"]}]},
            station_set=[{"station_id": "s1"}],
            travel_model=object(),
            platform_base_prices={"P1": 1.0},
            platform_sharing_rates={"P1": 0.4},
            platform_qualities={"P1": 0.9},
        )

        seed = build_environment_seed(environment)
        clone_a = clone_environment_from_seed(seed)
        clone_b = clone_environment_from_seed(seed)

        self.assertEqual(clone_a.tasks, clone_b.tasks)
        self.assertEqual(clone_a.local_couriers, clone_b.local_couriers)
        self.assertIs(clone_a.travel_model, clone_b.travel_model)

        clone_a.tasks.append({"task_id": "t2"})
        clone_a.local_couriers[0]["route"].append("C")

        self.assertEqual(len(clone_b.tasks), 1)
        self.assertEqual(clone_b.local_couriers[0]["route"], ["A"])

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


if __name__ == "__main__":
    unittest.main()
