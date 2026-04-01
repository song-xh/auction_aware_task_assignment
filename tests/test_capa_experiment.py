"""Tests for Chengdu experiment helpers built on top of the Phase 4 CAPA package."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from capa import CAPAConfig, Parcel
from capa.experiments import build_entities_from_locations, run_chengdu_experiment, save_experiment_plots
from capa.models import BatchReport, RunMetrics


class CAPAExperimentTests(unittest.TestCase):
    """Validate experiment helper behavior without touching the Chengdu graph."""

    def test_build_entities_from_locations_returns_requested_counts(self) -> None:
        """The helper should deterministically create the requested courier counts."""
        locations = ["n1", "n2", "n3", "n4", "n5", "n6"]

        local_couriers, platforms = build_entities_from_locations(
            locations=locations,
            local_courier_count=3,
            cooperating_platform_count=2,
            couriers_per_platform=2,
        )

        self.assertEqual(len(local_couriers), 3)
        self.assertEqual(len(platforms), 2)
        self.assertEqual([len(platform.couriers) for platform in platforms], [2, 2])

    def test_save_experiment_plots_writes_png_files(self) -> None:
        """The experiment plot helper should materialize PNG files for the three metrics."""
        batch_report = BatchReport(
            batch_index=1,
            batch_time=0,
            input_parcels=[Parcel("p1", "n1", 0, 10, 1.0, 8.0)],
            local_assignments=[],
            cross_assignments=[],
            unresolved_parcels=[],
            processing_time_seconds=0.02,
        )
        metrics = RunMetrics(total_revenue=8.0, completion_rate=1.0, batch_processing_time=0.02)

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)
            save_experiment_plots([batch_report], metrics, output_dir)

            self.assertTrue((output_dir / "tr_over_batches.png").exists())
            self.assertTrue((output_dir / "cr_over_batches.png").exists())
            self.assertTrue((output_dir / "bpt_over_batches.png").exists())

    def test_run_chengdu_experiment_uses_injected_environment_builder(self) -> None:
        """The official Chengdu experiment path should no longer depend on synthetic entity construction."""
        from tests.test_chengdu_runner import FakeLegacyCourier, FakeStation, FakeTask

        local_station = FakeStation(1, "S")
        partner_station = FakeStation(2, "PS")
        tasks = [FakeTask("t1", "T1", 0, 30, 1.0, 10.0)]
        local_courier = FakeLegacyCourier(num=1, location="L0", station=local_station)
        partner_courier = FakeLegacyCourier(num=2, location="P0", station=partner_station)
        from capa import DistanceMatrixTravelModel
        travel_model = DistanceMatrixTravelModel(
            distances={
                ("L0", "T1"): 2.0,
                ("T1", "S"): 2.0,
                ("L0", "S"): 4.0,
                ("P0", "T1"): 2.0,
                ("T1", "PS"): 2.0,
                ("P0", "PS"): 4.0,
            },
            speed=1.0,
        )

        def fake_builder(**_kwargs):
            return {
                "tasks": tasks,
                "local_couriers": [local_courier],
                "partner_couriers_by_platform": {"P1": [partner_courier]},
                "station_set": [local_station, partner_station],
                "travel_model": travel_model,
                "platform_base_prices": {"P1": 1.0},
                "platform_sharing_rates": {"P1": 0.4},
                "platform_qualities": {"P1": 1.0},
                "movement_callback": lambda local, partner, step, stations: None,
            }

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)
            with patch("capa.experiments.build_entities_from_locations", side_effect=AssertionError("synthetic builder must not be used")):
                result = run_chengdu_experiment(
                    data_dir=Path("Data"),
                    num_parcels=1,
                    local_courier_count=1,
                    cooperating_platform_count=1,
                    couriers_per_platform=1,
                    batch_size=60,
                    output_dir=output_dir,
                    env_builder=fake_builder,
                )

            self.assertEqual(len(result.matching_plan), 1)
            self.assertTrue((output_dir / "summary.json").exists())


if __name__ == "__main__":
    unittest.main()
