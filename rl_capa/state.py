"""State-construction helpers for the two RL-CAPA MDPs."""

from __future__ import annotations

from typing import Sequence

import numpy as np

from capa.cama import is_feasible_local_match
from capa.models import Courier, Parcel


def build_batch_state(
    pending_parcels: Sequence[Parcel],
    local_couriers: Sequence[Courier],
    travel_model: object,
    now: int,
    service_radius_meters: float | None = None,
) -> np.ndarray:
    """Construct the four-dimensional `S_b` feature vector from the paper.

    Args:
        pending_parcels: Pending local-platform parcels visible at the current batch boundary.
        local_couriers: Local-platform courier snapshots.
        travel_model: Shared travel model used for distance and time queries.
        now: Current batch-boundary time.
        service_radius_meters: Optional courier radius constraint.

    Returns:
        A float32 vector `(pending_count, available_courier_count, avg_distance, avg_urgency)`.
    """

    pending_count = float(len(pending_parcels))
    available_courier_count = float(sum(1 for courier in local_couriers if courier.available_from <= now))
    feasible_distances: list[float] = []
    urgency_terms: list[float] = []
    for parcel in pending_parcels:
        urgency_terms.append(max(0.0, float(parcel.deadline - now)) / max(float(parcel.deadline), 1.0))
        for courier in local_couriers:
            if not is_feasible_local_match(
                parcel=parcel,
                courier=courier,
                travel_model=travel_model,
                now=now,
                service_radius_meters=service_radius_meters,
            ):
                continue
            feasible_distances.append(float(travel_model.distance(courier.current_location, parcel.location)))
    average_distance = float(sum(feasible_distances) / len(feasible_distances)) if feasible_distances else 0.0
    average_urgency = float(sum(urgency_terms) / len(urgency_terms)) if urgency_terms else 0.0
    return np.array(
        [pending_count, available_courier_count, average_distance, average_urgency],
        dtype=np.float32,
    )


def build_parcel_state(
    parcel: Parcel,
    unassigned_count: int,
    current_time: int,
    batch_size: int,
) -> np.ndarray:
    """Construct the four-dimensional `S_m` feature vector from the paper.

    Args:
        parcel: Parcel currently considered by `M_m`.
        unassigned_count: Number of parcels in the current auction-pool candidate set.
        current_time: Current batch-boundary time.
        batch_size: Batch size selected by `M_b`.

    Returns:
        A float32 vector `(len(ΔΓ), t_tau, t_cur, Δb)`.
    """

    return np.array(
        [
            float(unassigned_count),
            float(parcel.deadline),
            float(current_time),
            float(batch_size),
        ],
        dtype=np.float32,
    )
