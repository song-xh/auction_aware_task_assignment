"""Regression for P3 state-dim extensions (review_0512.md)."""

from __future__ import annotations

import unittest

import numpy as np

from capa.models import Parcel
from rl_capa.state_builder import (
    STAGE1_STATE_DIM,
    STAGE2_STATE_DIM,
    build_stage1_state,
    build_stage2_states,
)


class Stage1StateDimTests(unittest.TestCase):
    """Stage-1 state must be 10-dimensional with drift-signal tail features."""

    def test_state_shape_is_ten(self) -> None:
        self.assertEqual(STAGE1_STATE_DIM, 10)
        state = build_stage1_state(
            pending_parcels=[],
            local_couriers=[],
            travel_model=None,
            now=0,
            recent_timeout_ratio=0.25,
            recent_unresolved_ratio=0.1,
        )
        self.assertEqual(state.shape, (10,))
        self.assertEqual(state.dtype, np.float32)
        self.assertAlmostEqual(float(state[-2]), 0.25)
        self.assertAlmostEqual(float(state[-1]), 0.1)

    def test_recent_features_default_to_zero(self) -> None:
        state = build_stage1_state(
            pending_parcels=[],
            local_couriers=[],
            travel_model=None,
            now=0,
        )
        self.assertEqual(state.shape, (10,))
        self.assertAlmostEqual(float(state[-2]), 0.0)
        self.assertAlmostEqual(float(state[-1]), 0.0)


class Stage2StateDimTests(unittest.TestCase):
    """Stage-2 per-parcel state must be 11-dimensional."""

    def _parcel(self, parcel_id: str = "p1", deadline: int = 200) -> Parcel:
        return Parcel(
            parcel_id=parcel_id,
            location=(0, 0),
            arrival_time=0,
            deadline=deadline,
            weight=1.0,
            fare=10.0,
        )

    def test_state_shape_is_eleven(self) -> None:
        self.assertEqual(STAGE2_STATE_DIM, 11)
        parcel = self._parcel()
        states = build_stage2_states(
            unassigned_parcels=[parcel],
            local_couriers=[],
            cross_courier_count=0,
            current_time=10,
            batch_size=20,
            local_payment_ratio=0.2,
            avg_cross_bid=0.0,
            observed_slack_by_parcel={"p1": 0.7},
            recent_timeout_ratio=0.3,
        )
        self.assertEqual(states[0].shape, (11,))
        self.assertAlmostEqual(float(states[0][-2]), 0.7)
        self.assertAlmostEqual(float(states[0][-1]), 0.3)

    def test_missing_slack_lookup_uses_zero(self) -> None:
        parcel = self._parcel(parcel_id="p2")
        states = build_stage2_states(
            unassigned_parcels=[parcel],
            local_couriers=[],
            cross_courier_count=0,
            current_time=10,
            batch_size=20,
            recent_timeout_ratio=0.0,
        )
        self.assertEqual(states[0].shape, (11,))
        self.assertAlmostEqual(float(states[0][-2]), 0.0)
        self.assertAlmostEqual(float(states[0][-1]), 0.0)


if __name__ == "__main__":
    unittest.main()
