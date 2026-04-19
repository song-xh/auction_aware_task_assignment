"""Actor-critic networks for RL-CAPA (spec Section 7, 9.1).

Four networks:
  - BatchSizeActor (pi1): s_t^(1) -> softmax over |A_b| batch sizes
  - CrossOrNotActor (pi2): s_{t,i}^(2) -> sigmoid P(cross=1), shared params
  - StateValueCritic (V1): s_t^(1) -> scalar value
  - ConditionalValueCritic (V2): mean-pooled s_t^(2) -> scalar value
"""

from __future__ import annotations

import torch
import torch.nn as nn
from torch.distributions import Bernoulli, Categorical


class BatchSizeActor(nn.Module):
    """pi1: select batch time-window size.

    Input:  s_t^(1) in R^4
    Hidden: 2-layer MLP, 128 units, ReLU
    Output: softmax over |A_b| discrete actions
    """

    def __init__(self, state_dim: int = 4, num_actions: int = 11, hidden_dim: int = 128) -> None:
        """Initialize pi1.

        Args:
            state_dim: Dimension of first-stage state (default 4).
            num_actions: Number of discrete batch-size actions |A_b|.
            hidden_dim: Hidden layer width.
        """
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, num_actions),
        )

    def forward(self, state: torch.Tensor) -> Categorical:
        """Compute action distribution.

        Args:
            state: Tensor of shape (batch, 4) or (4,).

        Returns:
            Categorical distribution over batch-size actions.
        """
        logits = self.net(state)
        return Categorical(logits=logits)


class CrossOrNotActor(nn.Module):
    """pi2: per-parcel cross-or-not decision, shared parameters.

    Input:  s_{t,i}^(2) in R^9 (already includes Delta_b = a_t^(1))
    Hidden: 2-layer MLP, 128 units, ReLU
    Output: sigmoid -> P(a_{t,i} = 1)
    """

    def __init__(self, state_dim: int = 9, hidden_dim: int = 128) -> None:
        """Initialize pi2.

        Args:
            state_dim: Dimension of per-parcel state (default 9).
            hidden_dim: Hidden layer width.
        """
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1),
        )

    def forward(self, state: torch.Tensor) -> Bernoulli:
        """Compute per-parcel cross probability.

        Args:
            state: Tensor of shape (batch, 9) or (9,).

        Returns:
            Bernoulli distribution for cross-or-not decision.
        """
        logit = self.net(state).squeeze(-1)
        return Bernoulli(logits=logit)


class StateValueCritic(nn.Module):
    """V1: state value before first-stage action.

    Input:  s_t^(1) in R^4
    Hidden: 2-layer MLP, 128 units, ReLU
    Output: scalar value
    """

    def __init__(self, state_dim: int = 4, hidden_dim: int = 128) -> None:
        """Initialize V1.

        Args:
            state_dim: Dimension of first-stage state (default 4).
            hidden_dim: Hidden layer width.
        """
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1),
        )

    def forward(self, state: torch.Tensor) -> torch.Tensor:
        """Compute state value.

        Args:
            state: Tensor of shape (batch, 4) or (4,).

        Returns:
            Scalar value tensor.
        """
        return self.net(state).squeeze(-1)


class ConditionalValueCritic(nn.Module):
    """V2: conditional state value after first-stage action.

    Input:  mean-pooled s_t^(2)_aggregated in R^9
            (a_t^(1) already included as Delta_b component)
    Hidden: 2-layer MLP, 128 units, ReLU
    Output: scalar value
    """

    def __init__(self, state_dim: int = 9, hidden_dim: int = 128) -> None:
        """Initialize V2.

        Args:
            state_dim: Dimension of aggregated stage-2 state (default 9).
            hidden_dim: Hidden layer width.
        """
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1),
        )

    def forward(self, state: torch.Tensor) -> torch.Tensor:
        """Compute conditional state value.

        Args:
            state: Tensor of shape (batch, 9) or (9,).

        Returns:
            Scalar value tensor.
        """
        return self.net(state).squeeze(-1)
