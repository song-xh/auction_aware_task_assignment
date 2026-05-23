"""State construction helpers for RL-CAPA (spec Section 3, 9.2).

Provides:
  - build_stage1_state: 6-dim s_t^(1) from environment
  - build_stage2_states: per-parcel 9/10-dim s_{t,i}^(2)
  - aggregate_stage2_states: mean-pooling for V2 input
  - RunningNormalizer: online feature normalization
"""

from __future__ import annotations

from typing import List, Sequence

import numpy as np

from capa.cama import is_feasible_local_match
from capa.models import Courier, Parcel


STAGE1_STATE_DIM = 8
STAGE2_STATE_DIM = 11
STAGE2_SERVICE_SLACK_DIM = STAGE2_STATE_DIM + 1


def get_stage2_state_dim(use_service_slack: bool = False) -> int:
    """Return the effective Stage-2 state dimension for one configuration."""

    return STAGE2_SERVICE_SLACK_DIM if use_service_slack else STAGE2_STATE_DIM


class RunningNormalizer:
    """Online running mean/std normalizer for feature vectors.

    Uses Welford's algorithm to track mean and variance incrementally.
    Normalizes features to zero mean and unit variance.
    """

    def __init__(self, dim: int, epsilon: float = 1e-8) -> None:
        """Initialize normalizer.

        Args:
            dim: Feature vector dimension.
            epsilon: Small constant to prevent division by zero.
        """
        self.dim = dim
        self.epsilon = epsilon
        self.count: int = 0
        self.mean = np.zeros(dim, dtype=np.float64)
        self.var = np.ones(dim, dtype=np.float64)
        self._m2 = np.zeros(dim, dtype=np.float64)

    def update(self, x: np.ndarray) -> None:
        """Update running statistics with one observation.

        Args:
            x: Feature vector of shape (dim,).
        """
        self.count += 1
        delta = x.astype(np.float64) - self.mean
        self.mean += delta / self.count
        delta2 = x.astype(np.float64) - self.mean
        self._m2 += delta * delta2
        self.var = self._m2 / max(self.count, 1) if self.count > 1 else np.ones(self.dim, dtype=np.float64)

    def normalize(self, x: np.ndarray) -> np.ndarray:
        """Normalize a feature vector using current running statistics.

        Args:
            x: Raw feature vector of shape (dim,).

        Returns:
            Normalized feature vector of shape (dim,), dtype float32.
        """
        std = np.sqrt(self.var + self.epsilon)
        return ((x.astype(np.float64) - self.mean) / std).astype(np.float32)

    def update_and_normalize(self, x: np.ndarray) -> np.ndarray:
        """Update stats then normalize in one call.

        Args:
            x: Raw feature vector.

        Returns:
            Normalized feature vector.
        """
        self.update(x)
        return self.normalize(x)


def build_stage1_state(
    pending_parcels: Sequence[Parcel],
    local_couriers: Sequence[Courier],
    travel_model: object,
    now: int,
    service_radius_meters: float | None = None,
    future_parcel_count: int = 0,
    future_courier_count: int = 0,
    delivered_ratio: float = 0.0,
    expired_ratio: float = 0.0,
) -> np.ndarray:
    """Construct the 8-dim first-stage state s_t^(1).

    Features (spec Section 3.1, extended for review_0507.md §8):
      [|Gamma_t^Loc|, |C_t^Loc|, N_Z^Gamma, N_Z^C, |D|, |T|,
       delivered_ratio, expired_ratio]

    Args:
        pending_parcels: Parcels awaiting assignment.
        local_couriers: Local courier snapshots.
        travel_model: Shared travel model for distance queries.
        now: Current batch-boundary time.
        service_radius_meters: Optional service radius constraint.
        future_parcel_count: True future parcel count inside the configured window.
        future_courier_count: True future local courier availability count.
        delivered_ratio: Fraction of total parcels already delivered/accepted.
        expired_ratio: Fraction of total parcels already past their deadline.

    Returns:
        Float32 array of shape (8,).
    """
    pending_count = float(len(pending_parcels))
    available_count = float(
        sum(1 for c in local_couriers if c.available_from <= now)
    )

    feasible_distances: List[float] = []
    urgency_terms: List[float] = []
    for parcel in pending_parcels:
        total_window = max(1.0, float(parcel.deadline) - float(parcel.arrival_time))
        urgency_terms.append(
            min(1.0, max(0.0, float(now) - float(parcel.arrival_time)) / total_window)
        )
        for courier in local_couriers:
            if not is_feasible_local_match(
                parcel, courier, travel_model, now,
                service_radius_meters=service_radius_meters,
            ):
                continue
            feasible_distances.append(
                float(travel_model.distance(courier.current_location, parcel.location))
            )

    avg_distance = (
        sum(feasible_distances) / len(feasible_distances)
        if feasible_distances else 0.0
    )
    avg_urgency = (
        sum(urgency_terms) / len(urgency_terms)
        if urgency_terms else 0.0
    )

    return np.array(
        [
            pending_count,
            available_count,
            float(future_parcel_count),
            float(future_courier_count),
            avg_distance,
            avg_urgency,
            float(delivered_ratio),
            float(expired_ratio),
        ],
        dtype=np.float32,
    )


def build_stage2_states(
    unassigned_parcels: Sequence[Parcel],
    local_couriers: Sequence[Courier],
    cross_courier_count: int,
    current_time: int,
    batch_size: int,
    local_payment_ratio: float = 0.2,
    avg_cross_bid: float = 0.0,
    normalized_service_slacks: Sequence[float] | None = None,
    local_feasible_flags: Sequence[float] | None = None,
    local_best_detour_ratios: Sequence[float] | None = None,
) -> List[np.ndarray]:
    """Construct per-parcel second-stage states s_{t,i}^(2).

    Features (spec Section 3.2, revised to use deadline-relative time
    so the per-parcel state remains discriminative across episodes):
      [remaining_seconds_i, urgency_ratio_i, v_tau_i, |DeltaGamma_t|,
       |C_t^Loc|, u_bar_t^Loc, |C_t^Cross|, b_bar_t^Cross, Delta_b]

    ``remaining_seconds_i = max(0, deadline_i - current_time)`` and
    ``urgency_ratio_i = clip01((current_time - arrival_i) / (deadline_i - arrival_i))``
    replace the prior raw `(deadline_i, current_time)` tuple. The raw
    tuple collapsed to ~zero variance under running normalization because
    deadlines and elapsed times sit in narrow absolute bands.

    Args:
        unassigned_parcels: Parcels not assigned by CAMA.
        local_couriers: Local courier snapshots.
        cross_courier_count: Total couriers across cooperating platforms.
        current_time: Current environment time.
        batch_size: First-stage action a_t^(1).
        local_payment_ratio: Zeta for Rc_hat estimation.
        avg_cross_bid: Sliding average of recent cross-platform bids.
        normalized_service_slacks: Optional per-parcel normalized service-slack
            feature values appended as the last Stage-2 dimension.

    Returns:
        List of float32 arrays, each shape (9,) or (10,).
    """
    available_local = float(
        sum(1 for c in local_couriers if c.available_from <= current_time)
    )
    capacities = [
        max(0.0, c.capacity - c.current_load)
        for c in local_couriers
        if c.available_from <= current_time
    ]
    avg_remaining_cap = (
        sum(capacities) / len(capacities) if capacities else 0.0
    )
    unassigned_count = float(len(unassigned_parcels))

    states: List[np.ndarray] = []
    for index, parcel in enumerate(unassigned_parcels):
        v_tau = parcel.fare * (1.0 - local_payment_ratio)
        total_window = max(1.0, float(parcel.deadline) - float(parcel.arrival_time))
        remaining_seconds = max(0.0, float(parcel.deadline) - float(current_time))
        urgency_ratio = min(
            1.0,
            max(0.0, float(current_time) - float(parcel.arrival_time)) / total_window,
        )
        local_feasible = (
            1.0 if local_feasible_flags is None else float(local_feasible_flags[index])
        )
        local_best_detour = (
            0.0
            if local_best_detour_ratios is None
            else float(np.clip(local_best_detour_ratios[index], 0.0, 1.0))
        )
        state_values = [
            remaining_seconds,
            urgency_ratio,
            v_tau,
            unassigned_count,
            available_local,
            avg_remaining_cap,
            float(cross_courier_count),
            avg_cross_bid,
            float(batch_size),
            local_feasible,
            local_best_detour,
        ]
        if normalized_service_slacks is not None:
            state_values.append(float(normalized_service_slacks[index]))
        state = np.array(
            state_values,
            dtype=np.float32,
        )
        states.append(state)
    return states


def aggregate_stage2_states(
    states: List[np.ndarray],
    state_dim: int | None = None,
) -> np.ndarray:
    """Mean-pool per-parcel states for V2 input.

    Args:
        states: List of shape-(9,) arrays from build_stage2_states.

    Returns:
        Float32 array of shape `(state_dim,)` — mean across all parcels.
        Returns zeros if input is empty.
    """
    if not states:
        return np.zeros(STAGE2_STATE_DIM if state_dim is None else state_dim, dtype=np.float32)
    return np.mean(states, axis=0).astype(np.float32)
