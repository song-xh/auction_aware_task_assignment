"""Integration tests for the end-to-end CAPA runner."""

import unittest

from capa import (
    CAPAConfig,
    CooperatingPlatform,
    Courier,
    DistanceMatrixTravelModel,
    Parcel,
    run_capa,
)


class CAPARunnerTests(unittest.TestCase):
    """Validate batch accumulation, carry-over, and metric reporting."""

    def setUp(self) -> None:
        """Construct a deterministic travel model for runner tests."""
        self.travel = DistanceMatrixTravelModel(
            distances={
                ("LS", "LD"): 10.0,
                ("LS", "A"): 4.0,
                ("A", "LD"): 6.0,
                ("LS", "B"): 15.0,
                ("B", "LD"): 5.0,
                ("PS", "PD"): 10.0,
                ("PS", "B"): 4.0,
                ("B", "PD"): 6.0,
            },
            speed=1.0,
        )

    def test_run_capa_combines_local_cross_and_metrics(self) -> None:
        """Algorithm 1 should return a matching plan and batch metrics."""
        config = CAPAConfig(
            batch_size=2,
            utility_balance_gamma=0.5,
            threshold_omega=1.0,
            local_payment_ratio_zeta=0.2,
            local_sharing_rate_mu1=0.5,
            cross_platform_sharing_rate_mu2=0.4,
        )
        local_couriers = [
            Courier(
                courier_id="local-1",
                current_location="LS",
                depot_location="LD",
                capacity=10.0,
                current_load=1.0,
            )
        ]
        platforms = [
            CooperatingPlatform(
                platform_id="P1",
                base_price=1.0,
                sharing_rate_gamma=0.4,
                historical_quality=1.0,
                couriers=[
                    Courier(
                        courier_id="cross-1",
                        current_location="PS",
                        depot_location="PD",
                        capacity=10.0,
                        current_load=0.0,
                        alpha=0.0,
                        beta=0.8,
                        service_score=1.0,
                    )
                ],
            )
        ]
        parcels = [
            Parcel("p1", "A", arrival_time=0, deadline=20, weight=2.0, fare=10.0),
            Parcel("p2", "B", arrival_time=1, deadline=40, weight=2.0, fare=10.0),
        ]

        result = run_capa(parcels, local_couriers, platforms, self.travel, config, timeline_end=1)

        self.assertEqual(len(result.matching_plan), 2)
        self.assertEqual([a.mode for a in result.matching_plan], ["local", "cross"])
        self.assertAlmostEqual(result.metrics.total_revenue, 11.4)
        self.assertAlmostEqual(result.metrics.completion_rate, 1.0)
        self.assertGreaterEqual(result.metrics.batch_processing_time, 0.0)

    def test_run_capa_retries_unassigned_parcels_in_later_batches(self) -> None:
        """Parcels left unresolved in one batch should reappear in the next batch."""
        config = CAPAConfig(
            batch_size=1,
            threshold_omega=1.0,
            local_payment_ratio_zeta=0.2,
            local_sharing_rate_mu1=0.5,
            cross_platform_sharing_rate_mu2=0.4,
        )
        local_couriers = []
        platforms = [
            CooperatingPlatform(
                platform_id="P1",
                base_price=1.0,
                sharing_rate_gamma=0.4,
                historical_quality=1.0,
                couriers=[
                    Courier(
                        courier_id="cross-1",
                        current_location="PS",
                        depot_location="PD",
                        capacity=10.0,
                        current_load=0.0,
                        available_from=2,
                        alpha=0.0,
                        beta=0.8,
                        service_score=1.0,
                    )
                ],
            )
        ]
        parcels = [
            Parcel("p1", "B", arrival_time=0, deadline=40, weight=2.0, fare=10.0),
        ]

        result = run_capa(parcels, local_couriers, platforms, self.travel, config, timeline_end=2)

        self.assertEqual(len(result.matching_plan), 1)
        self.assertEqual(result.matching_plan[0].mode, "cross")
        self.assertEqual(result.unassigned_parcels, [])
        self.assertEqual(len(result.batch_reports), 3)


if __name__ == "__main__":
    unittest.main()
