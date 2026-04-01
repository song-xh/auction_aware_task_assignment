"""Unit tests for the DAPA / DLAM auction logic."""

import unittest

from capa import (
    CAPAConfig,
    CooperatingPlatform,
    Courier,
    DistanceMatrixTravelModel,
    Parcel,
    run_dapa,
)
from capa.dapa import compute_fpsa_bid, compute_platform_payment_limit


class CAPAAuctionTests(unittest.TestCase):
    """Validate the two-layer cross-platform auction behavior."""

    def setUp(self) -> None:
        """Create deterministic parcel, travel, and platform fixtures."""
        self.travel = DistanceMatrixTravelModel(
            distances={
                ("S1", "D1"): 10.0,
                ("S1", "A"): 4.0,
                ("A", "D1"): 6.0,
                ("S2", "D2"): 10.0,
                ("S2", "A"): 4.0,
                ("A", "D2"): 6.0,
                ("S3", "D3"): 10.0,
                ("S3", "A"): 4.0,
                ("A", "D3"): 6.0,
            },
            speed=1.0,
        )
        self.config = CAPAConfig(
            local_sharing_rate_mu1=0.5,
            cross_platform_sharing_rate_mu2=0.4,
        )
        self.parcel = Parcel(
            parcel_id="p1",
            location="A",
            arrival_time=0,
            deadline=30,
            weight=1.0,
            fare=10.0,
        )

    def test_compute_fpsa_bid_matches_eq1_shape(self) -> None:
        """Eq.1 should use the platform base price and platform sharing rate."""
        courier = Courier(
            courier_id="c1",
            current_location="S1",
            depot_location="D1",
            capacity=10.0,
            current_load=0.0,
            alpha=0.0,
            beta=0.8,
            service_score=1.0,
        )
        platform = CooperatingPlatform(
            platform_id="P1",
            couriers=[courier],
            base_price=1.0,
            sharing_rate_gamma=0.4,
            historical_quality=0.5,
        )

        bid = compute_fpsa_bid(self.parcel, courier, platform, self.travel, self.config)

        self.assertAlmostEqual(bid, 2.6)

    def test_run_dapa_uses_second_lowest_payment_and_filters_by_limit(self) -> None:
        """DAPA should filter bids above P_lim and pay the second-lowest valid bid."""
        p1 = CooperatingPlatform(
            platform_id="P1",
            base_price=1.0,
            sharing_rate_gamma=0.4,
            historical_quality=0.5,
            couriers=[
                Courier(
                    courier_id="c1",
                    current_location="S1",
                    depot_location="D1",
                    capacity=10.0,
                    current_load=0.0,
                    alpha=0.0,
                    beta=0.8,
                    service_score=1.0,
                )
            ],
        )
        p2 = CooperatingPlatform(
            platform_id="P2",
            base_price=1.0,
            sharing_rate_gamma=0.5,
            historical_quality=1.0,
            couriers=[
                Courier(
                    courier_id="c2",
                    current_location="S2",
                    depot_location="D2",
                    capacity=10.0,
                    current_load=0.0,
                    alpha=0.0,
                    beta=0.6,
                    service_score=1.0,
                )
            ],
        )
        p3 = CooperatingPlatform(
            platform_id="P3",
            base_price=5.0,
            sharing_rate_gamma=1.0,
            historical_quality=1.0,
            couriers=[
                Courier(
                    courier_id="c3",
                    current_location="S3",
                    depot_location="D3",
                    capacity=10.0,
                    current_load=0.0,
                    alpha=0.0,
                    beta=1.0,
                    service_score=1.0,
                )
            ],
        )

        result = run_dapa([self.parcel], [p1, p2, p3], self.travel, self.config, now=0)

        self.assertEqual(len(result.cross_assignments), 1)
        assignment = result.cross_assignments[0]
        self.assertEqual(assignment.platform_id, "P1")
        self.assertAlmostEqual(assignment.platform_payment, 6.5)
        self.assertAlmostEqual(assignment.courier_payment, 2.6)
        self.assertEqual([p.parcel_id for p in result.unassigned_parcels], [])
        self.assertAlmostEqual(compute_platform_payment_limit(self.parcel, self.config), 9.0)

    def test_single_platform_case_uses_eq3_single_bidder_payment(self) -> None:
        """A single valid platform should be paid its own first-layer bid plus mu2 * p_tau."""
        platform = CooperatingPlatform(
            platform_id="P1",
            base_price=1.0,
            sharing_rate_gamma=0.4,
            historical_quality=0.5,
            couriers=[
                Courier(
                    courier_id="c1",
                    current_location="S1",
                    depot_location="D1",
                    capacity=10.0,
                    current_load=0.0,
                    alpha=0.0,
                    beta=0.8,
                    service_score=1.0,
                )
            ],
        )

        result = run_dapa([self.parcel], [platform], self.travel, self.config, now=0)

        assignment = result.cross_assignments[0]
        self.assertEqual(assignment.platform_id, "P1")
        self.assertAlmostEqual(assignment.courier_payment, 2.6)
        self.assertAlmostEqual(assignment.platform_payment, 6.6)


if __name__ == "__main__":
    unittest.main()
