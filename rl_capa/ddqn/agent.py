"""DDQN agent wrapper shared by the batch-level and parcel-level RL-CAPA decisions."""

from __future__ import annotations

import random
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from torch import optim

from rl_capa.transitions import TransitionBatch

from .networks import BatchQNetwork, CrossQNetwork
from .replay_buffer import ReplayBuffer


class DDQNAgent:
    """Implement epsilon-greedy action selection and Double DQN updates."""

    def __init__(
        self,
        state_dim: int,
        action_dim: int,
        learning_rate: float,
        discount_factor: float,
        epsilon_start: float,
        epsilon_end: float,
        epsilon_decay_steps: int,
        target_update_interval: int,
    ) -> None:
        """Create the online/target Q-networks and optimization state.

        Args:
            state_dim: Observation dimensionality.
            action_dim: Discrete action count.
            learning_rate: RMSprop learning rate.
            discount_factor: Discount factor `gamma`.
            epsilon_start: Initial exploration rate.
            epsilon_end: Final exploration rate.
            epsilon_decay_steps: Linear decay horizon in environment steps.
            target_update_interval: Hard target-sync interval in optimization steps.
        """

        if state_dim <= 0:
            raise ValueError("state_dim must be positive.")
        if action_dim <= 0:
            raise ValueError("action_dim must be positive.")
        if epsilon_decay_steps <= 0:
            raise ValueError("epsilon_decay_steps must be positive.")
        if target_update_interval <= 0:
            raise ValueError("target_update_interval must be positive.")
        self._state_dim = state_dim
        self._action_dim = action_dim
        self._discount_factor = discount_factor
        self._epsilon_start = epsilon_start
        self._epsilon_end = epsilon_end
        self._epsilon_decay_steps = epsilon_decay_steps
        self._target_update_interval = target_update_interval
        self._selection_steps = 0
        self._optimization_steps = 0
        network_class = CrossQNetwork if action_dim == 2 else BatchQNetwork
        if action_dim == 2:
            self.online_network = network_class(input_dim=state_dim)
            self.target_network = network_class(input_dim=state_dim)
        else:
            self.online_network = network_class(input_dim=state_dim, action_dim=action_dim)
            self.target_network = network_class(input_dim=state_dim, action_dim=action_dim)
        self.target_network.load_state_dict(self.online_network.state_dict())
        self.target_network.eval()
        self.optimizer = optim.RMSprop(self.online_network.parameters(), lr=learning_rate)

    def current_epsilon(self) -> float:
        """Return the current epsilon value under linear decay."""

        decay_progress = min(1.0, self._selection_steps / float(self._epsilon_decay_steps))
        return self._epsilon_start + decay_progress * (self._epsilon_end - self._epsilon_start)

    def select_action(self, state: np.ndarray, explore: bool = True) -> int:
        """Choose one action under epsilon-greedy exploration.

        Args:
            state: One state vector.
            explore: Whether epsilon exploration is enabled.

        Returns:
            One discrete action index.
        """

        epsilon = self.current_epsilon() if explore else 0.0
        self._selection_steps += 1
        if random.random() < epsilon:
            return random.randrange(self._action_dim)
        with torch.no_grad():
            state_tensor = torch.as_tensor(state, dtype=torch.float32).unsqueeze(0)
            q_values = self.online_network(state_tensor)
            return int(torch.argmax(q_values, dim=1).item())

    def train_step(self, buffer: ReplayBuffer, batch_size: int) -> float:
        """Perform one Double DQN optimization step.

        Args:
            buffer: Replay buffer to sample from.
            batch_size: Mini-batch size.

        Returns:
            Scalar TD loss.
        """

        batch = buffer.sample(batch_size)
        loss = self._compute_loss(batch)
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        self._optimization_steps += 1
        self.maybe_update_target()
        return float(loss.item())

    def maybe_update_target(self) -> None:
        """Synchronize the target network on the configured hard-update interval."""

        if self._optimization_steps % self._target_update_interval == 0:
            self.target_network.load_state_dict(self.online_network.state_dict())

    def save(self, checkpoint_path: Path) -> None:
        """Persist network and optimizer state to disk.

        Args:
            checkpoint_path: Destination checkpoint path.
        """

        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "state_dim": self._state_dim,
                "action_dim": self._action_dim,
                "online_network": self.online_network.state_dict(),
                "target_network": self.target_network.state_dict(),
                "optimizer": self.optimizer.state_dict(),
                "selection_steps": self._selection_steps,
                "optimization_steps": self._optimization_steps,
                "epsilon_start": self._epsilon_start,
                "epsilon_end": self._epsilon_end,
                "epsilon_decay_steps": self._epsilon_decay_steps,
                "discount_factor": self._discount_factor,
                "target_update_interval": self._target_update_interval,
            },
            checkpoint_path,
        )

    @classmethod
    def load(cls, checkpoint_path: Path, learning_rate: float | None = None) -> "DDQNAgent":
        """Reconstruct one DDQN agent from a saved checkpoint.

        Args:
            checkpoint_path: Path previously written by `save`.
            learning_rate: Optional optimizer learning-rate override.

        Returns:
            Reconstructed DDQN agent.
        """

        payload = torch.load(checkpoint_path, map_location="cpu")
        agent = cls(
            state_dim=int(payload["state_dim"]),
            action_dim=int(payload["action_dim"]),
            learning_rate=float(learning_rate if learning_rate is not None else 0.001),
            discount_factor=float(payload["discount_factor"]),
            epsilon_start=float(payload["epsilon_start"]),
            epsilon_end=float(payload["epsilon_end"]),
            epsilon_decay_steps=int(payload["epsilon_decay_steps"]),
            target_update_interval=int(payload["target_update_interval"]),
        )
        agent.online_network.load_state_dict(payload["online_network"])
        agent.target_network.load_state_dict(payload["target_network"])
        agent.optimizer.load_state_dict(payload["optimizer"])
        agent._selection_steps = int(payload["selection_steps"])
        agent._optimization_steps = int(payload["optimization_steps"])
        return agent

    def _compute_loss(self, batch: TransitionBatch) -> torch.Tensor:
        """Compute one Double DQN TD loss from a sampled mini-batch.

        Args:
            batch: Sampled replay transitions.

        Returns:
            Scalar loss tensor.
        """

        states = torch.as_tensor(batch.states, dtype=torch.float32)
        actions = torch.as_tensor(batch.actions, dtype=torch.int64).unsqueeze(1)
        rewards = torch.as_tensor(batch.rewards, dtype=torch.float32)
        next_states = torch.as_tensor(batch.next_states, dtype=torch.float32)
        dones = torch.as_tensor(batch.dones, dtype=torch.float32)

        current_q = self.online_network(states).gather(1, actions).squeeze(1)
        with torch.no_grad():
            next_actions = torch.argmax(self.online_network(next_states), dim=1, keepdim=True)
            next_q = self.target_network(next_states).gather(1, next_actions).squeeze(1)
            targets = rewards + (1.0 - dones) * self._discount_factor * next_q
        return F.mse_loss(current_q, targets)
