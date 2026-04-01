"""Unit tests for the local CAMA logic."""

import unittest

from capa import CAPAConfig, Courier, DistanceMatrixTravelModel, Parcel, run_cama
from capa.utility import calculate_threshold, calculate_utility


class CAPALocalTests(unittest.TestCase):
    """Validate utility computation and local matching behavior."""

    def setUp(self) -> None:
        """Create a deterministic travel model shared by the tests."""
        self.travel = DistanceMatrixTravelModel(
            distances={
                ("S1", "D1"): 10.0,
                ("S1", "A"): 4.0,
                ("S1", "B"): 100.0,
                ("S2", "A"): 100.0,
                ("A", "D1"): 6.0,
                ("S2", "D2"): 10.0,
                ("S2", "B"): 20.0,
                ("B", "D1"): 100.0,
                ("B", "D2"): 5.0,
            },
            speed=1.0,
        )

    def test_calculate_utility_matches_eq6(self) -> None:
        """Eq.6 should combine the capacity and detour ratios linearly."""
        courier = Courier(
            courier_id="c1",
            current_location="S1",
            depot_location="D1",
            capacity=10.0,
            current_load=1.0,
        )
        parcel = Parcel(
            parcel_id="p1",
            location="A",
            arrival_time=0,
            deadline=20,
            weight=2.0,
            fare=10.0,
        )
        config = CAPAConfig(utility_balance_gamma=0.25)

        utility = calculate_utility(parcel, courier, self.travel, config)

        self.assertAlmostEqual(utility.capacity_ratio, 0.7)
        self.assertAlmostEqual(utility.detour_ratio, 1.0)
        self.assertAlmostEqual(utility.value, 0.925)

    def test_threshold_uses_all_pairs_in_mt(self) -> None:
        """Eq.7 should average over every feasible pair in M_t."""
        threshold = calculate_threshold([0.9, 0.6, 0.3], omega=0.5)
        self.assertAlmostEqual(threshold, 0.3)

    def test_calculate_utility_handles_zero_detour_same_node_case(self) -> None:
        """A parcel already on the courier node should be treated as zero extra detour."""
        courier = Courier(
            courier_id="c1",
            current_location="A",
            depot_location="A",
            capacity=10.0,
            current_load=1.0,
        )
        parcel = Parcel(
            parcel_id="p1",
            location="A",
            arrival_time=0,
            deadline=20,
            weight=2.0,
            fare=10.0,
        )
        config = CAPAConfig(utility_balance_gamma=0.25)

        utility = calculate_utility(parcel, courier, self.travel, config)

        self.assertAlmostEqual(utility.detour_ratio, 1.0)
        self.assertAlmostEqual(utility.value, 0.925)

    def test_run_cama_splits_local_and_cross_by_threshold(self) -> None:
        """CAMA should keep only high-utility candidate-best pairs locally."""
        config = CAPAConfig(utility_balance_gamma=0.5, threshold_omega=1.0)
        couriers = [
            Courier(
                courier_id="c1",
                current_location="S1",
                depot_location="D1",
                capacity=10.0,
                current_load=1.0,
            ),
            Courier(
                courier_id="c2",
                current_location="S2",
                depot_location="D2",
                capacity=10.0,
                current_load=1.0,
            ),
        ]
        parcels = [
            Parcel(
                parcel_id="p1",
                location="A",
                arrival_time=0,
                deadline=20,
                weight=2.0,
                fare=10.0,
            ),
            Parcel(
                parcel_id="p2",
                location="B",
                arrival_time=0,
                deadline=40,
                weight=2.0,
                fare=8.0,
            ),
        ]

        result = run_cama(parcels, couriers, self.travel, config, now=0)

        self.assertEqual([a.parcel.parcel_id for a in result.local_assignments], ["p1"])
        self.assertEqual([p.parcel_id for p in result.auction_pool], ["p2"])
        self.assertEqual(len(result.matching_pairs), 1)
        self.assertEqual(len(result.candidate_best_pairs), 2)
        self.assertGreater(result.threshold, 0.0)


if __name__ == "__main__":
    unittest.main()
