"""Stage-2-only RL-CAPA ablation trainer.

This ablation fixes the batch duration and trains only the shared parcel-level
cross-or-local policy used by RL-CAPA's second stage.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Mapping

import numpy as np
import torch
import torch.nn as nn

from rl_capa.networks import ConditionalValueCritic, CrossOrNotActor
from rl_capa.state_builder import STAGE2_STATE_DIM, RunningNormalizer, aggregate_stage2_states
from rl_capa.trainer import RLCAPATrainer, TrainingConfig
from rl_capa.utils import compute_discounted_returns, select_torch_device


@dataclass
class Stage2StepRecord:
    """One fixed-batch stage-2 ablation training step."""

    s2_agg: torch.Tensor
    log_prob_2: torch.Tensor
    entropy_2: torch.Tensor
    reward: float
    num_cross: int = 0
    num_unassigned: int = 0
    acted: bool = False


@dataclass
class Stage2EpisodeLog:
    """Logged metrics for one stage-2 ablation episode."""

    episode: int
    total_reward: float
    loss_pi2: float
    loss_v2: float
    steps: int
    assignments: int
    fixed_batch_size: int
    cross_rate: float = 0.0
    entropy_pi2: float = 0.0
    batch_sizes: List[int] = field(default_factory=list)
    mean_batch_size: float = 0.0
    loss_pi1: float = 0.0
    loss_v1: float = 0.0
    entropy_pi1: float = 0.0
    truncated: bool = False


class Stage2RLCAPATrainer:
    """Train only the RL-CAPA parcel-level cross-or-local actor."""

    def __init__(
        self,
        env: object,
        config: TrainingConfig,
        fixed_batch_size: int,
        device: str | None = None,
    ) -> None:
        """Initialize the stage-2 trainer.

        Args:
            env: RLCAPAEnv-compatible environment.
            config: Shared actor-critic training hyperparameters.
            fixed_batch_size: Fixed batch duration used for every step.
            device: Optional torch device override.
        """

        if fixed_batch_size <= 0:
            raise ValueError("fixed_batch_size must be positive.")
        self.env = env
        self.config = config
        self.fixed_batch_size = fixed_batch_size
        self.device = select_torch_device(config.device if device is None else device)
        self.pi2 = CrossOrNotActor(state_dim=STAGE2_STATE_DIM, hidden_dim=128).to(self.device)
        self.v2 = ConditionalValueCritic(state_dim=STAGE2_STATE_DIM, hidden_dim=128).to(self.device)
        self.opt_pi2 = torch.optim.Adam(self.pi2.parameters(), lr=config.lr_actor)
        self.opt_v2 = torch.optim.Adam(self.v2.parameters(), lr=config.lr_critic)
        self.norm_s2 = RunningNormalizer(dim=STAGE2_STATE_DIM)
        self.history: list[Stage2EpisodeLog] = []

    def train(
        self,
        progress_callback: Callable[[Mapping[str, float | int | bool]], None] | None = None,
    ) -> list[Stage2EpisodeLog]:
        """Run fixed-batch stage-2-only training."""

        self.history = []
        for episode_idx in range(self.config.num_episodes):
            log = self._run_episode(episode_idx)
            self.history.append(log)
            if progress_callback is not None:
                progress_callback(self._build_progress_payload(log))
        return self.history

    def _run_episode(self, episode_idx: int) -> Stage2EpisodeLog:
        """Collect one episode and update the stage-2 actor/critic."""

        self.env.reset()
        buffer: list[Stage2StepRecord] = []
        step = 0
        while not self.env.is_done() and step < self.config.max_steps_per_episode:
            step += 1
            buffer.append(self._collect_step())
        if not buffer:
            self.env.finalize_episode()
            return Stage2EpisodeLog(
                episode=episode_idx,
                total_reward=0.0,
                loss_pi2=0.0,
                loss_v2=0.0,
                steps=0,
                assignments=0,
                fixed_batch_size=self.fixed_batch_size,
            )

        self.env.finalize_episode()
        terminal_reward = self.env.pop_terminal_delivered_revenue()
        if terminal_reward:
            buffer[-1].reward += terminal_reward

        returns = compute_discounted_returns(
            rewards=[record.reward for record in buffer],
            discount_factor=self.config.discount_factor,
        )
        loss_pi2, loss_v2 = self._update_networks(buffer, returns)
        total_unassigned = sum(record.num_unassigned for record in buffer)
        total_cross = sum(record.num_cross for record in buffer)
        return Stage2EpisodeLog(
            episode=episode_idx,
            total_reward=sum(record.reward for record in buffer),
            loss_pi2=loss_pi2,
            loss_v2=loss_v2,
            steps=step,
            assignments=len(self.env.delivered_parcels()),
            fixed_batch_size=self.fixed_batch_size,
            cross_rate=total_cross / max(total_unassigned, 1),
            entropy_pi2=sum(record.entropy_2.detach().item() for record in buffer) / max(total_unassigned, 1),
            batch_sizes=[self.fixed_batch_size for _ in buffer],
            mean_batch_size=float(self.fixed_batch_size),
            truncated=not self.env.is_done(),
        )

    def _collect_step(self) -> Stage2StepRecord:
        """Apply a fixed batch duration, sample parcel actions, and finalize the batch."""

        self.env.apply_batch_size(self.fixed_batch_size)
        batch_parcels = self.env.current_eligible_parcels()
        s2_list = self.env.get_stage2_states(batch_parcels)
        if s2_list:
            s2_normed = [self.norm_s2.update_and_normalize(state) for state in s2_list]
            s2_tensor = torch.from_numpy(np.stack(s2_normed)).to(self.device)
            dist2 = self.pi2(s2_tensor)
            actions_2 = dist2.sample()
            decisions = {
                parcel.parcel_id: int(action.item())
                for parcel, action in zip(batch_parcels, actions_2)
            }
            s2_agg_raw = aggregate_stage2_states(s2_list)
            s2_agg_norm = self.norm_s2.normalize(s2_agg_raw)
            s2_agg_tensor = torch.from_numpy(s2_agg_norm).to(self.device)
            log_prob_2 = dist2.log_prob(actions_2).sum()
            entropy_2 = dist2.entropy().sum()
            num_cross = sum(1 for action in actions_2 if action.item() == 1)
            acted = True
        else:
            decisions = {}
            s2_agg_tensor = torch.zeros(STAGE2_STATE_DIM, device=self.device)
            log_prob_2 = torch.tensor(0.0, device=self.device)
            entropy_2 = torch.tensor(0.0, device=self.device)
            num_cross = 0
            acted = False
        reward = self.env.apply_stage2_decisions(decisions)
        return Stage2StepRecord(
            s2_agg=s2_agg_tensor,
            log_prob_2=log_prob_2,
            entropy_2=entropy_2,
            reward=reward,
            num_cross=num_cross,
            num_unassigned=len(batch_parcels),
            acted=acted,
        )

    def _update_networks(
        self,
        buffer: list[Stage2StepRecord],
        returns: list[float],
    ) -> tuple[float, float]:
        """Update the stage-2 actor and critic from one episode buffer."""

        s2_agg_batch = torch.stack([record.s2_agg for record in buffer])
        returns_tensor = torch.tensor(returns, dtype=torch.float32, device=self.device)
        v2_values = self.v2(s2_agg_batch)
        loss_v2 = ((v2_values - returns_tensor.detach()) ** 2).mean()
        self.opt_v2.zero_grad()
        loss_v2.backward()
        nn.utils.clip_grad_norm_(self.v2.parameters(), self.config.max_grad_norm)
        self.opt_v2.step()

        acted_records = [record for record in buffer if record.acted]
        if not acted_records:
            return 0.0, loss_v2.item()
        acted_indices = [index for index, record in enumerate(buffer) if record.acted]
        log_probs_2 = torch.stack([record.log_prob_2 for record in acted_records])
        entropies_2 = torch.stack([record.entropy_2 for record in acted_records])
        with torch.no_grad():
            v2_detached = self.v2(s2_agg_batch)
            adv_2 = returns_tensor - v2_detached
            adv_2 = adv_2[acted_indices]
            if self.config.normalize_advantages:
                adv_2 = RLCAPATrainer._normalize_advantages(adv_2)

        loss_pi2 = -(log_probs_2 * adv_2).mean() - self.config.entropy_coeff * entropies_2.mean()
        self.opt_pi2.zero_grad()
        loss_pi2.backward()
        nn.utils.clip_grad_norm_(self.pi2.parameters(), self.config.max_grad_norm)
        self.opt_pi2.step()
        return loss_pi2.item(), loss_v2.item()

    def _build_progress_payload(self, episode_log: Stage2EpisodeLog) -> dict[str, float | int | bool]:
        """Serialize one stage-2 episode into the shared progress schema."""

        return {
            "episode": episode_log.episode + 1,
            "total_episodes": self.config.num_episodes,
            "total_reward": episode_log.total_reward,
            "steps": episode_log.steps,
            "assignments": episode_log.assignments,
            "avg_batch_size": episode_log.mean_batch_size,
            "cross_rate": episode_log.cross_rate,
            "entropy_pi1": episode_log.entropy_pi1,
            "entropy_pi2": episode_log.entropy_pi2,
            "truncated": episode_log.truncated,
        }
