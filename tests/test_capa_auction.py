"""Tests for cross-platform CAPA shortlist behavior."""

from __future__ import annotations

import unittest

from capa.dapa import build_cross_candidate_shortlist, run_dapa
from capa.models import CAPAConfig, CooperatingPlatform, Courier, Parcel

from tests.capa_test_support import FakeGeoIndex, FakeTravelModel


class CrossShortlistTest(unittest.TestCase):
    """Verify partner shortlist reuse narrows DAPA candidate evaluation."""

    def test_build_cross_candidate_shortlist_groups_candidates_per_platform(self) -> None:
        """Cross shortlist should retain only cheap-filter survivors per platform."""

        parcel = Parcel(parcel_id="p1", location="parcel", arrival_time=0, deadline=20, weight=2.0, fare=10.0)
        platform = CooperatingPlatform(
            platform_id="P1",
            couriers=[
                Courier(courier_id="winner", current_location="near", depot_location="depot", capacity=10.0, alpha=0.5, beta=0.5, service_score=0.8),
                Courier(courier_id="too-far", current_location="far", depot_location="depot", capacity=10.0, alpha=0.5, beta=0.5, service_score=0.8),
            ],
            base_price=2.0,
            sharing_rate_gamma=0.5,
            historical_quality=1.0,
        )
        geo_index = FakeGeoIndex(lower_bounds={("near", "parcel"): 5.0, ("far", "parcel"): 50.0})

        shortlist = build_cross_candidate_shortlist(
            [parcel],
            [platform],
            now=0,
            service_radius_meters=10.0,
            geo_index=geo_index,
            speed_m_per_s=1.0,
        )

        self.assertEqual(
            [courier.courier_id for courier in shortlist[parcel.parcel_id][platform.platform_id]],
            ["winner"],
        )

    def test_run_dapa_can_reuse_cross_shortlist_without_changing_winner(self) -> None:
        """Running DAPA with an explicit shortlist should preserve the winning courier."""

        parcel = Parcel(parcel_id="p1", location="parcel", arrival_time=0, deadline=20, weight=1.0, fare=10.0)
        winner = Courier(courier_id="winner", current_location="near", depot_location="depot", capacity=10.0, alpha=0.5, beta=0.5, service_score=0.8)
        loser = Courier(courier_id="loser", current_location="far", depot_location="depot", capacity=10.0, alpha=0.5, beta=0.5, service_score=0.8)
        platform = CooperatingPlatform(
            platform_id="P1",
            couriers=[winner, loser],
            base_price=2.0,
            sharing_rate_gamma=0.5,
            historical_quality=1.0,
        )
        travel_model = FakeTravelModel(
            distances={
                ("near", "parcel"): 2.0,
                ("parcel", "depot"): 4.0,
                ("near", "depot"): 6.0,
                ("far", "parcel"): 8.0,
                ("far", "depot"): 6.0,
            }
        )
        config = CAPAConfig(local_sharing_rate_mu1=0.5, cross_platform_sharing_rate_mu2=0.4)

        full_result = run_dapa([parcel], [platform], travel_model, config, now=0)
        winning_courier_id = full_result.cross_assignments[0].courier.courier_id
        shortlisted_courier = winner if winning_courier_id == winner.courier_id else loser
        shortlisted_result = run_dapa(
            [parcel],
            [platform],
            travel_model,
            config,
            now=0,
            candidate_couriers_by_parcel={parcel.parcel_id: {platform.platform_id: [shortlisted_courier]}},
        )

        self.assertEqual(
            [assignment.courier.courier_id for assignment in full_result.cross_assignments],
            [winning_courier_id],
        )
        self.assertEqual(
            [assignment.courier.courier_id for assignment in shortlisted_result.cross_assignments],
            [winning_courier_id],
        )

    def test_run_dapa_rejects_invalid_platform_base_price_constraint(self) -> None:
        """DAPA should fail when p_min violates the paper base-price constraint."""

        parcel = Parcel(parcel_id="p1", location="parcel", arrival_time=0, deadline=20, weight=1.0, fare=10.0)
        platform = CooperatingPlatform(
            platform_id="P1",
            couriers=[
                Courier(courier_id="winner", current_location="near", depot_location="depot", capacity=10.0, alpha=0.5, beta=0.5, service_score=0.8),
            ],
            base_price=3.0,
            sharing_rate_gamma=0.5,
            historical_quality=1.0,
        )
        travel_model = FakeTravelModel(
            distances={
                ("near", "parcel"): 2.0,
                ("parcel", "depot"): 4.0,
                ("near", "depot"): 6.0,
            }
        )

        with self.assertRaises(ValueError):
            run_dapa([parcel], [platform], travel_model, CAPAConfig(), now=0)


if __name__ == "__main__":
    unittest.main()
