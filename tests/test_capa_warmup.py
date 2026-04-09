"""Tests for shortlist-driven CAPA distance warmup."""

from __future__ import annotations

import unittest

from capa.models import Courier, Parcel
from capa.utility import BatchDistanceMatrix

from tests.capa_test_support import FakeTravelModel


class BatchDistanceWarmupTest(unittest.TestCase):
    """Verify batch warmup scopes exact distances to explicit candidate pairs."""

    def test_precompute_for_candidate_pairs_warms_only_shortlisted_pairs(self) -> None:
        """Warmup should not touch parcels or couriers outside the explicit shortlist."""

        courier_a = Courier(
            courier_id="c1",
            current_location="start-a",
            depot_location="depot-a",
            capacity=10.0,
            route_locations=["mid-a"],
        )
        courier_b = Courier(
            courier_id="c2",
            current_location="start-b",
            depot_location="depot-b",
            capacity=10.0,
            route_locations=["mid-b"],
        )
        parcel_a = Parcel(parcel_id="p1", location="parcel-a", arrival_time=0, deadline=100, weight=1.0, fare=10.0)
        parcel_b = Parcel(parcel_id="p2", location="parcel-b", arrival_time=0, deadline=100, weight=1.0, fare=10.0)
        travel_model = FakeTravelModel(
            distances={
                ("start-a", "mid-a"): 3.0,
                ("mid-a", "depot-a"): 4.0,
                ("start-a", "parcel-a"): 2.0,
                ("parcel-a", "mid-a"): 2.0,
                ("mid-a", "parcel-a"): 2.0,
                ("parcel-a", "depot-a"): 5.0,
                ("start-b", "mid-b"): 3.0,
                ("mid-b", "depot-b"): 4.0,
                ("start-b", "parcel-b"): 2.0,
                ("parcel-b", "mid-b"): 2.0,
                ("mid-b", "parcel-b"): 2.0,
                ("parcel-b", "depot-b"): 5.0,
            }
        )
        bdm = BatchDistanceMatrix(travel_model)

        bdm.precompute_for_candidate_pairs([(courier_a, parcel_a)])

        self.assertEqual(
            set(travel_model.distance_calls),
            {
                ("start-a", "mid-a"),
                ("mid-a", "depot-a"),
                ("start-a", "parcel-a"),
                ("parcel-a", "mid-a"),
                ("mid-a", "parcel-a"),
                ("parcel-a", "depot-a"),
            },
        )
        self.assertNotIn(("start-b", "parcel-b"), travel_model.distance_calls)
        self.assertNotIn(("start-a", "parcel-b"), travel_model.distance_calls)


if __name__ == "__main__":
    unittest.main()
