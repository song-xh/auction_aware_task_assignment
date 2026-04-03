"""Tests for RL-CAPA state construction helpers."""

from __future__ import annotations

import unittest

import numpy as np

from capa.models import Courier, Parcel


class _LinearTravelModel:
    """Provide deterministic distances and travel times for RL state tests."""

    def distance(self, start: object, end: object) -> float:
        """Return an absolute-distance metric in meters."""
        return float(abs(int(end) - int(start)))

    def travel_time(self, start: object, end: object) -> float:
        """Return the same linear metric as travel time in seconds."""
        return self.distance(start, end)


class RLCAPAStateTests(unittest.TestCase):
    """Validate the M_b and M_m state builders from the paper."""

    def test_build_batch_state_matches_four_component_definition(self) -> None:
        """S_b should expose pending count, available courier count, average distance, and urgency."""
        from rl_capa.state import build_batch_state

        parcels = [
            Parcel(parcel_id="t1", location=1, arrival_time=0, deadline=100, weight=1.0, fare=10.0),
            Parcel(parcel_id="t2", location=3, arrival_time=0, deadline=200, weight=1.0, fare=12.0),
        ]
        couriers = [
            Courier(courier_id="c1", current_location=0, depot_location=0, capacity=5.0, current_load=0.0),
            Courier(courier_id="c2", current_location=4, depot_location=4, capacity=5.0, current_load=0.0),
        ]

        state = build_batch_state(
            pending_parcels=parcels,
            local_couriers=couriers,
            travel_model=_LinearTravelModel(),
            now=0,
        )

        self.assertIsInstance(state, np.ndarray)
        self.assertEqual(state.shape, (4,))
        self.assertEqual(state[0], 2.0)
        self.assertEqual(state[1], 2.0)
        self.assertAlmostEqual(state[2], 2.0)
        self.assertAlmostEqual(state[3], 1.0)

    def test_build_parcel_state_matches_four_component_definition(self) -> None:
        """S_m should expose pool size, parcel deadline, current time, and chosen batch size."""
        from rl_capa.state import build_parcel_state

        parcel = Parcel(parcel_id="t1", location=1, arrival_time=0, deadline=120, weight=1.0, fare=10.0)

        state = build_parcel_state(
            parcel=parcel,
            unassigned_count=3,
            current_time=30,
            batch_size=60,
        )

        self.assertIsInstance(state, np.ndarray)
        self.assertEqual(state.shape, (4,))
        self.assertTrue(np.array_equal(state, np.array([3.0, 120.0, 30.0, 60.0], dtype=np.float32)))


if __name__ == "__main__":
    unittest.main()
