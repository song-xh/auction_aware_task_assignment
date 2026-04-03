"""Configuration models for RL-CAPA environments, DDQN, and training."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RLCAPAConfig:
    """Store RL-CAPA environment parameters derived from the paper.

    Args:
        min_batch_size: Lower bound `h_L` of the discrete batch-size action space.
        max_batch_size: Upper bound `h_M` of the discrete batch-size action space.
        step_seconds: Time step used when advancing the legacy Chengdu environment.
    """

    min_batch_size: int
    max_batch_size: int
    step_seconds: int = 60

    def batch_action_values(self) -> list[int]:
        """Return the discrete batch durations represented by `A_b`."""
        if self.min_batch_size <= 0:
            raise ValueError("min_batch_size must be positive.")
        if self.max_batch_size < self.min_batch_size:
            raise ValueError("max_batch_size must be greater than or equal to min_batch_size.")
        return list(range(self.min_batch_size, self.max_batch_size + 1))

    def batch_duration_from_action_index(self, action_index: int) -> int:
        """Map one discrete `M_b` action index to its concrete batch duration in seconds.

        Args:
            action_index: Zero-based DDQN action index.

        Returns:
            The batch duration represented by the action.
        """

        values = self.batch_action_values()
        if action_index < 0 or action_index >= len(values):
            raise ValueError(f"Unsupported batch action index {action_index}.")
        return values[action_index]

    def batch_duration_to_action_index(self, batch_duration: int) -> int:
        """Map one concrete batch duration back to the discrete DDQN action index.

        Args:
            batch_duration: Concrete batch duration in seconds.

        Returns:
            Zero-based DDQN action index.
        """

        values = self.batch_action_values()
        if batch_duration not in values:
            raise ValueError(f"Unsupported batch duration {batch_duration}.")
        return values.index(batch_duration)


@dataclass(frozen=True)
class RLTrainingConfig:
    """Store DDQN training hyperparameters for joint RL-CAPA optimization.

    Args:
        episodes: Number of training episodes.
        replay_capacity: Capacity of each replay buffer.
        replay_warmup: Minimum transitions required before optimization.
        batch_size: Mini-batch size sampled during optimization.
        learning_rate: RMSprop learning rate.
        discount_factor: Discount factor `gamma`.
        epsilon_start: Initial epsilon for exploration.
        epsilon_end: Final epsilon for exploration.
        epsilon_decay_steps: Number of steps over which epsilon decays.
        target_update_interval: Hard target-network update interval in optimizer steps.
        random_seed: Random seed used for reproducibility.
    """

    episodes: int = 10
    replay_capacity: int = 50_000
    replay_warmup: int = 64
    batch_size: int = 64
    learning_rate: float = 0.001
    discount_factor: float = 0.9
    epsilon_start: float = 1.0
    epsilon_end: float = 0.01
    epsilon_decay_steps: int = 10_000
    target_update_interval: int = 100
    random_seed: int = 1
