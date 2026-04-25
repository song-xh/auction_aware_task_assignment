"""Tests for local CAPA shortlist behavior."""

from __future__ import annotations

import unittest

from capa.cama import build_local_candidate_shortlist, run_cama
from capa.models import CAPAConfig, Courier, Parcel, ThresholdHistory

from tests.capa_test_support import FakeGeoIndex, FakeTravelModel


class LocalShortlistTest(unittest.TestCase):
    """Verify obvious local losers are filtered before exact routing."""

    def test_build_local_candidate_shortlist_uses_only_cheap_filters(self) -> None:
        """Availability, capacity, geo deadline, and geo radius should prune the shortlist."""

        parcel = Parcel(parcel_id="p1", location="parcel", arrival_time=0, deadline=20, weight=2.0, fare=10.0)
        winner = Courier(courier_id="winner", current_location="near", depot_location="depot", capacity=10.0, alpha=0.5, beta=0.5)
        unavailable = Courier(
            courier_id="late",
            current_location="near",
            depot_location="depot",
            capacity=10.0,
            available_from=30,
            alpha=0.5,
            beta=0.5,
        )
        overloaded = Courier(
            courier_id="full",
            current_location="near",
            depot_location="depot",
            capacity=1.0,
            current_load=1.0,
            alpha=0.5,
            beta=0.5,
        )
        travel_model = FakeTravelModel(
            distances={
                ("near", "parcel"): 5.0,
                ("parcel", "depot"): 5.0,
                ("near", "depot"): 10.0,
            }
        )
        geo_index = FakeGeoIndex(
            lower_bounds={
                ("near", "parcel"): 5.0,
                ("far", "parcel"): 50.0,
            }
        )
        shortlist = build_local_candidate_shortlist(
            [parcel],
            [
                winner,
                unavailable,
                overloaded,
                Courier(courier_id="too-far", current_location="far", depot_location="depot", capacity=10.0, alpha=0.5, beta=0.5),
            ],
            now=0,
            service_radius_meters=10.0,
            geo_index=geo_index,
            speed_m_per_s=1.0,
        )

        self.assertEqual([courier.courier_id for courier in shortlist[parcel.parcel_id]], ["winner"])
        self.assertEqual(travel_model.distance_calls, [])

    def test_run_cama_can_reuse_local_shortlist_without_changing_assignment(self) -> None:
        """Running CAMA with an explicit shortlist should preserve the winning assignment."""

        parcel = Parcel(parcel_id="p1", location="parcel", arrival_time=0, deadline=20, weight=1.0, fare=10.0)
        winner = Courier(courier_id="winner", current_location="near", depot_location="depot", capacity=10.0, alpha=0.5, beta=0.5)
        loser = Courier(courier_id="loser", current_location="far", depot_location="depot", capacity=10.0, alpha=0.5, beta=0.5)
        travel_model = FakeTravelModel(
            distances={
                ("near", "parcel"): 2.0,
                ("parcel", "depot"): 4.0,
                ("near", "depot"): 6.0,
                ("far", "parcel"): 8.0,
                ("far", "depot"): 6.0,
            }
        )
        config = CAPAConfig(utility_balance_gamma=0.5, threshold_omega=1.0)

        full_result = run_cama([parcel], [winner, loser], travel_model, config, now=0)
        shortlisted_result = run_cama(
            [parcel],
            [winner, loser],
            travel_model,
            config,
            now=0,
            candidate_couriers_by_parcel={parcel.parcel_id: [winner]},
        )

        self.assertEqual([assignment.courier.courier_id for assignment in full_result.local_assignments], ["winner"])
        self.assertEqual(
            [assignment.courier.courier_id for assignment in shortlisted_result.local_assignments],
            ["winner"],
        )

    def test_run_cama_threshold_history_accumulates_across_batches(self) -> None:
        """CAPA runtime threshold should use cumulative feasible-pair history."""

        config = CAPAConfig(utility_balance_gamma=1.0, threshold_omega=1.0)
        travel_model = FakeTravelModel(
            distances={
                ("depot", "p-high"): 1.0,
                ("p-high", "depot"): 1.0,
                ("depot", "p-low"): 1.0,
                ("p-low", "depot"): 1.0,
            }
        )
        history = ThresholdHistory()
        high = Parcel(parcel_id="high", location="p-high", arrival_time=0, deadline=20, weight=1.0, fare=10.0)
        low = Parcel(parcel_id="low", location="p-low", arrival_time=20, deadline=40, weight=5.0, fare=10.0)
        first_result = run_cama(
            [high],
            [Courier(courier_id="c-high", current_location="depot", depot_location="depot", capacity=10.0)],
            travel_model,
            config,
            now=0,
            threshold_history=history,
        )
        second_result = run_cama(
            [low],
            [Courier(courier_id="c-low", current_location="depot", depot_location="depot", capacity=10.0)],
            travel_model,
            config,
            now=20,
            threshold_history=history,
        )
        batch_local_result = run_cama(
            [low],
            [Courier(courier_id="c-local", current_location="depot", depot_location="depot", capacity=10.0)],
            travel_model,
            config,
            now=20,
        )

        self.assertAlmostEqual(first_result.threshold, 0.9)
        self.assertAlmostEqual(second_result.threshold, 0.7)
        self.assertEqual([assignment.parcel.parcel_id for assignment in first_result.local_assignments], ["high"])
        self.assertEqual(second_result.local_assignments, [])
        self.assertEqual([parcel.parcel_id for parcel in second_result.auction_pool], ["low"])
        self.assertEqual([assignment.parcel.parcel_id for assignment in batch_local_result.local_assignments], ["low"])


if __name__ == "__main__":
    unittest.main()
