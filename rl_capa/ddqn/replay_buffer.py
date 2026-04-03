"""Replay-buffer implementation shared by the two RL-CAPA DDQN agents."""

from __future__ import annotations

import random
from collections import deque
from typing import Deque

import numpy as np

from rl_capa.transitions import Transition, TransitionBatch


class ReplayBuffer:
    """Store transitions and sample uniformly for DDQN optimization."""

    def __init__(self, capacity: int) -> None:
        """Create one bounded replay buffer.

        Args:
            capacity: Maximum number of transitions retained.
        """

        if capacity <= 0:
            raise ValueError("Replay buffer capacity must be positive.")
        self._capacity = capacity
        self._storage: Deque[Transition] = deque(maxlen=capacity)

    def __len__(self) -> int:
        """Return the number of currently stored transitions."""

        return len(self._storage)

    def push(self, transition: Transition) -> None:
        """Append one transition to the replay buffer.

        Args:
            transition: Transition to store.
        """

        self._storage.append(transition)

    def sample(self, batch_size: int) -> TransitionBatch:
        """Sample one uniformly random mini-batch of transitions.

        Args:
            batch_size: Number of transitions to sample.

        Returns:
            Stacked transition tensors as numpy arrays.
        """

        if batch_size <= 0:
            raise ValueError("Replay batch size must be positive.")
        if batch_size > len(self._storage):
            raise ValueError("Cannot sample more transitions than currently stored.")
        sampled = random.sample(list(self._storage), batch_size)
        return TransitionBatch(
            states=np.stack([transition.state for transition in sampled]).astype(np.float32),
            actions=np.asarray([transition.action for transition in sampled], dtype=np.int64),
            rewards=np.asarray([transition.reward for transition in sampled], dtype=np.float32),
            next_states=np.stack([transition.next_state for transition in sampled]).astype(np.float32),
            dones=np.asarray([transition.done for transition in sampled], dtype=np.float32),
        )
