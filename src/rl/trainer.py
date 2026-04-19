"""RL-CAPA training loop (spec Section 8).

Implements the two-stage hierarchical actor-critic training with:
  - 4 independent networks (pi1, pi2, V1, V2)
  - 4 independent Adam optimizers
  - Detached advantages: A1 = V2 - V1, A2 = R_hat - V2
  - Backward-cumulated discounted returns
  - Per-parcel factorized log_prob_2 = sum_i log pi2(a_i | s_i)
  - Optional entropy bonus and gradient clipping
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import torch
import torch.nn as nn

from src.rl.networks import (
    BatchSizeActor,
    ConditionalValueCritic,
    CrossOrNotActor,
    StateValueCritic,
)
from src.rl.state_builder import RunningNormalizer, aggregate_stage2_states


@dataclass
class TrainingConfig:
    """Hyperparameters for RL-CAPA training (spec Section 10).

    Args:
        num_episodes: Total training episodes.
        discount_factor: Gamma for discounted returns.
        lr_actor: Learning rate for both actors.
        lr_critic: Learning rate for both critics.
        entropy_coeff: Entropy bonus coefficient (prevents premature convergence).
        max_grad_norm: Gradient clipping threshold.
        max_steps_per_episode: Safety limit on steps per episode.
    """

    num_episodes: int = 500
    discount_factor: float = 0.9
    lr_actor: float = 0.001
    lr_critic: float = 0.001
    entropy_coeff: float = 0.01
    max_grad_norm: float = 0.5
    max_steps_per_episode: int = 500


@dataclass
class StepRecord:
    """One step's data in the episode buffer.

    Args:
        s1: First-stage state tensor (4,).
        a1_index: Sampled batch-size action index.
        log_prob_1: Log probability of a1 under pi1.
        s2_agg: Mean-pooled second-stage state tensor (9,).
        log_prob_2: Sum of per-parcel log probs under pi2.
        entropy_1: Entropy of pi1 distribution at this step.
        entropy_2: Sum of per-parcel entropies of pi2.
        reward: R_t from environment.
        batch_duration: Chosen batch duration in seconds.
        num_cross: Number of parcels sent to auction (a=1).
        num_unassigned: Total unassigned parcels at this step.
    """

    s1: torch.Tensor
    a1_index: int
    log_prob_1: torch.Tensor
    s2_agg: torch.Tensor
    log_prob_2: torch.Tensor
    entropy_1: torch.Tensor
    entropy_2: torch.Tensor
    reward: float
    batch_duration: int = 0
    num_cross: int = 0
    num_unassigned: int = 0


@dataclass
class EpisodeLog:
    """Logged metrics for one training episode.

    Args:
        episode: Episode index.
        total_reward: Sum of R_t over all steps.
        loss_pi1: Actor 1 policy gradient loss.
        loss_pi2: Actor 2 policy gradient loss.
        loss_v1: Critic 1 value loss.
        loss_v2: Critic 2 value loss.
        steps: Number of environment steps.
        assignments: Number of accepted assignments.
    """

    episode: int
    total_reward: float
    loss_pi1: float
    loss_pi2: float
    loss_v1: float
    loss_v2: float
    steps: int
    assignments: int
    batch_sizes: List[int] = field(default_factory=list)
    cross_rate: float = 0.0


class RLCAPATrainer:
    """Two-stage hierarchical actor-critic trainer for RL-CAPA.

    Manages 4 networks, 4 optimizers, episode collection, and updates.
    Follows spec Section 8 pseudocode exactly.
    """

    def __init__(
        self,
        env: object,
        config: TrainingConfig,
        num_batch_actions: int = 11,
        device: str = "cpu",
    ) -> None:
        """Initialize trainer with environment and networks.

        Args:
            env: RLCAPAEnv instance.
            config: Training hyperparameters.
            num_batch_actions: Size of discrete batch-size action space |A_b|.
            device: Torch device string.
        """
        self.env = env
        self.config = config
        self.device = torch.device(device)

        # 4 networks (spec Section 7)
        self.pi1 = BatchSizeActor(
            state_dim=4, num_actions=num_batch_actions, hidden_dim=128
        ).to(self.device)
        self.pi2 = CrossOrNotActor(state_dim=9, hidden_dim=128).to(self.device)
        self.v1 = StateValueCritic(state_dim=4, hidden_dim=128).to(self.device)
        self.v2 = ConditionalValueCritic(state_dim=9, hidden_dim=128).to(self.device)

        # 4 independent optimizers (spec Section 6.4)
        self.opt_pi1 = torch.optim.Adam(self.pi1.parameters(), lr=config.lr_actor)
        self.opt_pi2 = torch.optim.Adam(self.pi2.parameters(), lr=config.lr_actor)
        self.opt_v1 = torch.optim.Adam(self.v1.parameters(), lr=config.lr_critic)
        self.opt_v2 = torch.optim.Adam(self.v2.parameters(), lr=config.lr_critic)

        # Running normalizers for feature vectors
        self.norm_s1 = RunningNormalizer(dim=4)
        self.norm_s2 = RunningNormalizer(dim=9)

        # Batch action values for index-to-duration mapping
        self._batch_action_values: List[int] = []

        # Training history
        self.history: List[EpisodeLog] = []

    def train(self, batch_action_values: List[int]) -> List[EpisodeLog]:
        """Run the full training loop.

        Args:
            batch_action_values: Ordered list of batch durations for A_b.

        Returns:
            List of per-episode logs.
        """
        self._batch_action_values = batch_action_values
        self.history = []

        for episode_idx in range(self.config.num_episodes):
            log = self._run_episode(episode_idx)
            self.history.append(log)

        return self.history

    def _run_episode(self, episode_idx: int) -> EpisodeLog:
        """Collect one episode and update all 4 networks.

        Args:
            episode_idx: Zero-based episode index.

        Returns:
            Episode log with reward and losses.
        """
        self.env.reset()
        episode_buffer: List[StepRecord] = []
        step = 0

        while not self.env.is_done() and step < self.config.max_steps_per_episode:
            step += 1
            record = self._collect_step()
            episode_buffer.append(record)

        if not episode_buffer:
            return EpisodeLog(
                episode=episode_idx,
                total_reward=0.0,
                loss_pi1=0.0,
                loss_pi2=0.0,
                loss_v1=0.0,
                loss_v2=0.0,
                steps=0,
                assignments=0,
            )

        # Compute discounted returns (backward cumulation)
        returns = self._compute_discounted_returns(episode_buffer)

        # Update networks
        loss_pi1, loss_pi2, loss_v1, loss_v2 = self._update_networks(
            episode_buffer, returns
        )

        total_reward = sum(r.reward for r in episode_buffer)
        batch_sizes = [r.batch_duration for r in episode_buffer]
        total_cross = sum(r.num_cross for r in episode_buffer)
        total_unassigned = sum(r.num_unassigned for r in episode_buffer)
        cross_rate = total_cross / max(total_unassigned, 1)
        return EpisodeLog(
            episode=episode_idx,
            total_reward=total_reward,
            loss_pi1=loss_pi1,
            loss_pi2=loss_pi2,
            loss_v1=loss_v1,
            loss_v2=loss_v2,
            steps=step,
            assignments=len(self.env.accepted_assignments()),
            batch_sizes=batch_sizes,
            cross_rate=cross_rate,
        )

    def _collect_step(self) -> StepRecord:
        """Collect one environment step with both policy stages.

        Returns:
            StepRecord with states, actions, log probs, and reward.
        """
        # === Stage 1: batch size selection ===
        s1_raw = self.env.get_stage1_state()
        s1_norm = self.norm_s1.update_and_normalize(s1_raw)
        s1_tensor = torch.from_numpy(s1_norm).to(self.device)

        dist1 = self.pi1(s1_tensor)
        a1_index = dist1.sample()
        log_prob_1 = dist1.log_prob(a1_index)
        entropy_1 = dist1.entropy()
        batch_duration = self._batch_action_values[a1_index.item()]

        # Apply batch size -> advances time, accumulates parcels
        self.env.apply_batch_size(batch_duration)

        # === CAMA local matching ===
        local_assignments, unassigned = self.env.run_local_matching()

        # === Stage 2: per-parcel cross-or-not ===
        s2_list = self.env.get_stage2_states(unassigned)

        num_unassigned = len(unassigned)
        num_cross = 0

        if s2_list:
            # Normalize and stack per-parcel states
            s2_normed = [self.norm_s2.update_and_normalize(s) for s in s2_list]
            s2_tensor = torch.from_numpy(np.stack(s2_normed)).to(self.device)

            dist2 = self.pi2(s2_tensor)
            actions_2 = dist2.sample()
            # log_prob_2 = sum_i log pi2(a_i | s_i) -- factorized
            log_prob_2 = dist2.log_prob(actions_2).sum()
            entropy_2 = dist2.entropy().sum()

            # Build decisions dict
            decisions = {
                p.parcel_id: int(a.item())
                for p, a in zip(unassigned, actions_2)
            }
            num_cross = sum(1 for a in actions_2 if a.item() == 1)

            # Mean-pool for V2 input
            s2_agg_raw = aggregate_stage2_states(s2_list)
            s2_agg_norm = self.norm_s2.normalize(s2_agg_raw)
            s2_agg_tensor = torch.from_numpy(s2_agg_norm).to(self.device)
        else:
            # No unassigned parcels -- pi2 doesn't act
            log_prob_2 = torch.tensor(0.0, device=self.device)
            entropy_2 = torch.tensor(0.0, device=self.device)
            decisions = {}
            s2_agg_tensor = torch.zeros(9, device=self.device)

        # Apply cross decisions -> DAPA + defer, returns R_t
        reward = self.env.apply_cross_decisions(decisions)

        return StepRecord(
            s1=s1_tensor,
            a1_index=a1_index.item(),
            log_prob_1=log_prob_1,
            s2_agg=s2_agg_tensor,
            log_prob_2=log_prob_2,
            entropy_1=entropy_1,
            entropy_2=entropy_2,
            reward=reward,
            batch_duration=batch_duration,
            num_cross=num_cross,
            num_unassigned=num_unassigned,
        )

    def _compute_discounted_returns(
        self, buffer: List[StepRecord]
    ) -> List[float]:
        """Compute backward-cumulated discounted returns R_hat_t.

        Args:
            buffer: Episode step records.

        Returns:
            List of discounted returns, one per step.
        """
        gamma = self.config.discount_factor
        returns: List[float] = [0.0] * len(buffer)
        running = 0.0
        for t in reversed(range(len(buffer))):
            running = buffer[t].reward + gamma * running
            returns[t] = running
        return returns

    def _update_networks(
        self,
        buffer: List[StepRecord],
        returns: List[float],
    ) -> tuple[float, float, float, float]:
        """Update all 4 networks from episode data.

        Follows spec Section 6:
          A1 = V2 - V1 (detached)
          A2 = R_hat - V2 (detached)
          4 losses backpropagated separately.

        Args:
            buffer: Episode step records.
            returns: Discounted returns per step.

        Returns:
            Tuple of (loss_pi1, loss_pi2, loss_v1, loss_v2) as floats.
        """
        # Stack episode data
        s1_batch = torch.stack([r.s1 for r in buffer])
        s2_agg_batch = torch.stack([r.s2_agg for r in buffer])
        returns_tensor = torch.tensor(returns, dtype=torch.float32, device=self.device)
        log_probs_1 = torch.stack([r.log_prob_1 for r in buffer])
        log_probs_2 = torch.stack([r.log_prob_2 for r in buffer])
        entropies_1 = torch.stack([r.entropy_1 for r in buffer])
        entropies_2 = torch.stack([r.entropy_2 for r in buffer])

        # --- Critic 1 update ---
        v1_values = self.v1(s1_batch)
        loss_v1 = ((v1_values - returns_tensor.detach()) ** 2).mean()
        self.opt_v1.zero_grad()
        loss_v1.backward()
        nn.utils.clip_grad_norm_(self.v1.parameters(), self.config.max_grad_norm)
        self.opt_v1.step()

        # --- Critic 2 update ---
        v2_values = self.v2(s2_agg_batch)
        loss_v2 = ((v2_values - returns_tensor.detach()) ** 2).mean()
        self.opt_v2.zero_grad()
        loss_v2.backward()
        nn.utils.clip_grad_norm_(self.v2.parameters(), self.config.max_grad_norm)
        self.opt_v2.step()

        # --- Advantages (detached) ---
        with torch.no_grad():
            v1_detached = self.v1(s1_batch)
            v2_detached = self.v2(s2_agg_batch)
            adv_1 = v2_detached - v1_detached       # A1 = V2 - V1
            adv_2 = returns_tensor - v2_detached     # A2 = R_hat - V2

        # --- Actor 1 update ---
        loss_pi1 = -(log_probs_1 * adv_1).mean() - self.config.entropy_coeff * entropies_1.mean()
        self.opt_pi1.zero_grad()
        loss_pi1.backward()
        nn.utils.clip_grad_norm_(self.pi1.parameters(), self.config.max_grad_norm)
        self.opt_pi1.step()

        # --- Actor 2 update ---
        loss_pi2 = -(log_probs_2 * adv_2).mean() - self.config.entropy_coeff * entropies_2.mean()
        self.opt_pi2.zero_grad()
        loss_pi2.backward()
        nn.utils.clip_grad_norm_(self.pi2.parameters(), self.config.max_grad_norm)
        self.opt_pi2.step()

        return (
            loss_pi1.item(),
            loss_pi2.item(),
            loss_v1.item(),
            loss_v2.item(),
        )
