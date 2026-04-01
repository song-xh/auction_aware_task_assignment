"""Tests for Chengdu experiment helpers built on top of the Phase 4 CAPA package."""

import tempfile
import unittest
from pathlib import Path

from capa import CAPAConfig, Parcel
from capa.experiments import build_metric_series, run_chengdu_experiment, run_chengdu_parameter_sweep, save_experiment_plots
from capa.models import Assignment, BatchReport, Courier, RunMetrics
from env.chengdu import LegacyChengduEnvironment


class CAPAExperimentTests(unittest.TestCase):
    """Validate experiment helper behavior without touching the Chengdu graph."""

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
            delivered_parcel_count=1,
        )
        metrics = RunMetrics(total_revenue=8.0, completion_rate=1.0, batch_processing_time=0.02, delivered_parcel_count=1, accepted_parcel_count=1)

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)
            save_experiment_plots([batch_report], metrics, output_dir)

            self.assertTrue((output_dir / "tr_over_batches.png").exists())
            self.assertTrue((output_dir / "cr_over_batches.png").exists())
            self.assertTrue((output_dir / "bpt_over_batches.png").exists())

    def test_build_metric_series_uses_delivered_parcels_for_cr(self) -> None:
        """Batch-level CR should follow delivered parcels rather than accepted assignments."""
        parcel = Parcel("p1", "n1", 0, 10, 1.0, 8.0)
        courier = Courier(courier_id="c1", current_location="n0", depot_location="d0", capacity=10.0)
        assignment = Assignment(
            parcel=parcel,
            courier=courier,
            mode="local",
            platform_id=None,
            courier_payment=1.6,
            platform_payment=1.6,
            local_platform_revenue=6.4,
            cooperating_platform_revenue=0.0,
            courier_revenue=1.6,
            utility_value=0.5,
        )
        batch_reports = [
            BatchReport(
                batch_index=1,
                batch_time=0,
                input_parcels=[parcel],
                local_assignments=[assignment],
                cross_assignments=[],
                unresolved_parcels=[],
                processing_time_seconds=0.01,
                delivered_parcel_count=0,
            ),
            BatchReport(
                batch_index=2,
                batch_time=60,
                input_parcels=[],
                local_assignments=[],
                cross_assignments=[],
                unresolved_parcels=[],
                processing_time_seconds=0.01,
                delivered_parcel_count=1,
            ),
        ]

        _, cr_values, _ = build_metric_series(batch_reports, total_parcels=1)

        self.assertEqual(cr_values, [0.0, 1.0])

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
            def movement_callback(local_couriers, partner_couriers, step, stations) -> None:
                for courier in [*local_couriers, *partner_couriers]:
                    if not courier.re_schedule:
                        continue
                    head = courier.re_schedule.pop(0)
                    courier.location = head.l_node
                    courier.re_weight -= head.weight

            return LegacyChengduEnvironment(
                tasks=tasks,
                local_couriers=[local_courier],
                partner_couriers_by_platform={"P1": [partner_courier]},
                station_set=[local_station, partner_station],
                travel_model=travel_model,
                platform_base_prices={"P1": 1.0},
                platform_sharing_rates={"P1": 0.4},
                platform_qualities={"P1": 1.0},
                movement_callback=movement_callback,
            )

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)
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

    def test_run_chengdu_parameter_sweep_writes_aggregate_summary(self) -> None:
        """The sweep helper should run one experiment per parameter value and persist an aggregate summary."""
        from capa.models import CAPAResult

        def fake_runner(**kwargs):
            batch_size = kwargs["batch_size"]
            metric_value = float(batch_size)
            output_dir = kwargs["output_dir"]
            output_dir.mkdir(parents=True, exist_ok=True)
            return CAPAResult(
                matching_plan=[],
                unassigned_parcels=[],
                batch_reports=[],
                metrics=RunMetrics(
                    total_revenue=metric_value,
                    completion_rate=metric_value / 100.0,
                    batch_processing_time=metric_value / 10.0,
                    delivered_parcel_count=int(metric_value),
                    accepted_parcel_count=int(metric_value),
                ),
                delivered_parcels=[],
            )

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)
            summary = run_chengdu_parameter_sweep(
                data_dir=Path("Data"),
                output_dir=output_dir,
                sweep_parameter="batch_size",
                sweep_values=[60, 120],
                fixed_config={
                    "num_parcels": 5,
                    "local_courier_count": 2,
                    "cooperating_platform_count": 1,
                    "couriers_per_platform": 1,
                    "batch_size": 60,
                },
                experiment_runner=fake_runner,
            )

            self.assertEqual([run["batch_size"] for run in summary["runs"]], [60, 120])
            self.assertTrue((output_dir / "summary.json").exists())


if __name__ == "__main__":
    unittest.main()
