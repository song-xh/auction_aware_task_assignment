"""Neural-network definitions for the two RL-CAPA DDQN agents."""

from __future__ import annotations

import torch
from torch import nn


class BatchQNetwork(nn.Module):
    """Approximate `Q_b(s_b, a_b)` over the discrete batch-size action space."""

    def __init__(self, input_dim: int, action_dim: int) -> None:
        """Initialize the MLP used by the batch-size DDQN agent.

        Args:
            input_dim: Dimensionality of `S_b`.
            action_dim: Number of discrete batch-size actions.
        """

        super().__init__()
        self.layers = nn.Sequential(
            nn.Linear(input_dim, 128),
            nn.ReLU(),
            nn.Linear(128, 128),
            nn.ReLU(),
            nn.Linear(128, action_dim),
        )

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        """Compute Q-values for every batch-size action.

        Args:
            inputs: Batched `S_b` tensor.

        Returns:
            Q-values with shape `(batch_size, action_dim)`.
        """

        return self.layers(inputs)


class CrossQNetwork(nn.Module):
    """Approximate `Q_m(s_m, a_m)` for parcel-level cross-or-not decisions."""

    def __init__(self, input_dim: int) -> None:
        """Initialize the MLP used by the parcel-level DDQN agent.

        Args:
            input_dim: Dimensionality of `S_m`.
        """

        super().__init__()
        self.layers = nn.Sequential(
            nn.Linear(input_dim, 128),
            nn.ReLU(),
            nn.Linear(128, 128),
            nn.ReLU(),
            nn.Linear(128, 2),
        )

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        """Compute Q-values for the two parcel actions.

        Args:
            inputs: Batched `S_m` tensor.

        Returns:
            Q-values with shape `(batch_size, 2)`.
        """

        return self.layers(inputs)
