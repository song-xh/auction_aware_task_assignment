"""Transition and step models shared by RL-CAPA environment and DDQN code."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import numpy as np

from capa.models import Assignment, Parcel


@dataclass(frozen=True)
class Transition:
    """Store one `(s, a, r, s', done)` transition."""

    state: np.ndarray
    action: int
    reward: float
    next_state: np.ndarray
    done: bool


@dataclass(frozen=True)
class TransitionBatch:
    """Store one replay-buffer mini-batch as stacked numpy arrays."""

    states: np.ndarray
    actions: np.ndarray
    rewards: np.ndarray
    next_states: np.ndarray
    dones: np.ndarray


@dataclass(frozen=True)
class BatchDecisionContext:
    """Store the intermediate RL-CAPA state after `M_b` and CAMA but before `M_m`.

    Args:
        batch_state: The current `S_b` observation used to choose the batch action.
        batch_duration: The batch size selected by `M_b`.
        batch_time: Current time after the batch accumulation step.
        batch_parcels: All parcels participating in the current batch.
        local_assignments: Local assignments already committed by CAMA.
        auction_pool: Parcels emitted by CAMA into `L_cr`.
        parcel_states: `S_m` states keyed by parcel identifier.
        resolved_parcel_transitions: Deferred or failed cross transitions resolved at this batch start.
    """

    batch_state: np.ndarray
    batch_duration: int
    batch_time: int
    batch_parcels: Sequence[Parcel]
    local_assignments: Sequence[Assignment]
    auction_pool: Sequence[Parcel]
    parcel_states: dict[str, np.ndarray]
    resolved_parcel_transitions: Sequence[Transition] = field(default_factory=tuple)


@dataclass(frozen=True)
class RLCAPAStepResult:
    """Store the finalized outputs of one RL-CAPA batch step."""

    batch_transition: Transition
    batch_reward: float
    parcel_transitions: Sequence[Transition]
    local_assignments: Sequence[Assignment]
    cross_assignments: Sequence[Assignment]
    next_batch_state: np.ndarray
    done: bool
