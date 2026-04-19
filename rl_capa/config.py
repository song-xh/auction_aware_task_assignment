"""Configuration models for the actor-critic RL-CAPA implementation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RLCAPAConfig:
    """Environment-level RL-CAPA parameters derived from the actor-critic spec."""

    min_batch_size: int
    max_batch_size: int
    step_seconds: int = 60

    def batch_action_values(self) -> list[int]:
        """Return the discrete batch-size action values ``A_b``."""

        if self.min_batch_size <= 0:
            raise ValueError("min_batch_size must be positive.")
        if self.max_batch_size < self.min_batch_size:
            raise ValueError("max_batch_size must be greater than or equal to min_batch_size.")
        return list(range(self.min_batch_size, self.max_batch_size + 1))

    def batch_duration_from_action_index(self, action_index: int) -> int:
        """Map one discrete action index to the represented batch duration."""

        values = self.batch_action_values()
        if action_index < 0 or action_index >= len(values):
            raise ValueError(f"Unsupported batch action index {action_index}.")
        return values[action_index]

    def batch_duration_to_action_index(self, batch_duration: int) -> int:
        """Map a concrete batch duration to its discrete action index."""

        values = self.batch_action_values()
        if batch_duration not in values:
            raise ValueError(f"Unsupported batch duration {batch_duration}.")
        return values.index(batch_duration)


@dataclass(frozen=True)
class RLTrainingConfig:
    """Actor-critic training hyperparameters for RL-CAPA."""

    episodes: int = 500
    discount_factor: float = 0.9
    lr_actor: float = 0.001
    lr_critic: float = 0.001
    entropy_coeff: float = 0.01
    max_grad_norm: float = 0.5
    max_steps_per_episode: int = 500
    device: str | None = None
