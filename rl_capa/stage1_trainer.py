"""Stage-1-only RL-CAPA ablation trainer.

This ablation keeps CAPA's CAMA thresholding and DAPA auction unchanged after
the selected batch duration. Only the first-stage batch-size policy is learned.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Mapping

import numpy as np
import torch
import torch.nn as nn

from rl_capa.networks import BatchSizeActor, StateValueCritic
from rl_capa.state_builder import STAGE1_STATE_DIM, RunningNormalizer
from rl_capa.trainer import RLCAPATrainer, TrainingConfig
from rl_capa.utils import compute_discounted_returns, select_torch_device


@dataclass
class Stage1StepRecord:
    """One stage-1 ablation training step."""

    s1: torch.Tensor
    a1_index: int
    log_prob_1: torch.Tensor
    entropy_1: torch.Tensor
    reward: float
    batch_duration: int = 0


@dataclass
class Stage1EpisodeLog:
    """Logged metrics for one stage-1 ablation episode."""

    episode: int
    total_reward: float
    loss_pi1: float
    loss_v1: float
    steps: int
    assignments: int
    batch_sizes: List[int] = field(default_factory=list)
    mean_batch_size: float = 0.0
    entropy_pi1: float = 0.0
    loss_pi2: float = 0.0
    loss_v2: float = 0.0
    cross_rate: float = 0.0
    entropy_pi2: float = 0.0
    truncated: bool = False


class Stage1RLCAPATrainer:
    """Train only the RL-CAPA batch-size actor while keeping CAPA matching."""

    def __init__(
        self,
        env: object,
        config: TrainingConfig,
        num_batch_actions: int,
        device: str | None = None,
    ) -> None:
        """Initialize the stage-1 trainer.

        Args:
            env: RLCAPAEnv-compatible environment.
            config: Shared actor-critic training hyperparameters.
            num_batch_actions: Number of discrete batch-duration actions.
            device: Optional torch device override.
        """

        self.env = env
        self.config = config
        self.device = select_torch_device(config.device if device is None else device)
        self.pi1 = BatchSizeActor(
            state_dim=STAGE1_STATE_DIM,
            num_actions=num_batch_actions,
            hidden_dim=128,
        ).to(self.device)
        self.v1 = StateValueCritic(state_dim=STAGE1_STATE_DIM, hidden_dim=128).to(self.device)
        self.opt_pi1 = torch.optim.Adam(self.pi1.parameters(), lr=config.lr_actor)
        self.opt_v1 = torch.optim.Adam(self.v1.parameters(), lr=config.lr_critic)
        self.norm_s1 = RunningNormalizer(dim=STAGE1_STATE_DIM)
        self._batch_action_values: list[int] = []
        self.history: list[Stage1EpisodeLog] = []

    def train(
        self,
        batch_action_values: list[int],
        progress_callback: Callable[[Mapping[str, float | int | bool]], None] | None = None,
    ) -> list[Stage1EpisodeLog]:
        """Run stage-1-only training.

        Args:
            batch_action_values: Ordered batch-duration action values.
            progress_callback: Optional per-episode progress sink.

        Returns:
            Per-episode training logs.
        """

        self._batch_action_values = list(batch_action_values)
        self.history = []
        for episode_idx in range(self.config.num_episodes):
            log = self._run_episode(episode_idx)
            self.history.append(log)
            if progress_callback is not None:
                progress_callback(self._build_progress_payload(log))
        return self.history

    def _run_episode(self, episode_idx: int) -> Stage1EpisodeLog:
        """Collect one episode and update the stage-1 actor/critic."""

        self.env.reset()
        buffer: list[Stage1StepRecord] = []
        step = 0
        while not self.env.is_done() and step < self.config.max_steps_per_episode:
            step += 1
            buffer.append(self._collect_step())
        if not buffer:
            self.env.finalize_episode()
            return Stage1EpisodeLog(
                episode=episode_idx,
                total_reward=0.0,
                loss_pi1=0.0,
                loss_v1=0.0,
                steps=0,
                assignments=0,
            )

        returns = compute_discounted_returns(
            rewards=[record.reward for record in buffer],
            discount_factor=self.config.discount_factor,
        )
        loss_pi1, loss_v1 = self._update_networks(buffer, returns)
        self.env.finalize_episode()
        batch_sizes = [record.batch_duration for record in buffer]
        return Stage1EpisodeLog(
            episode=episode_idx,
            total_reward=sum(record.reward for record in buffer),
            loss_pi1=loss_pi1,
            loss_v1=loss_v1,
            steps=step,
            assignments=len(self.env.delivered_parcels()),
            batch_sizes=batch_sizes,
            mean_batch_size=float(np.mean(batch_sizes)) if batch_sizes else 0.0,
            entropy_pi1=float(np.mean([record.entropy_1.detach().item() for record in buffer])),
            truncated=not self.env.is_done(),
        )

    def _collect_step(self) -> Stage1StepRecord:
        """Sample one batch duration and run standard CAPA on that batch."""

        s1_raw = self.env.get_stage1_state()
        s1_norm = self.norm_s1.update_and_normalize(s1_raw)
        s1_tensor = torch.from_numpy(s1_norm).to(self.device)
        dist1 = self.pi1(s1_tensor)
        a1_index = dist1.sample()
        batch_duration = self._batch_action_values[a1_index.item()]
        self.env.apply_batch_size(batch_duration)
        reward = self.env.apply_capa_batch()
        return Stage1StepRecord(
            s1=s1_tensor,
            a1_index=a1_index.item(),
            log_prob_1=dist1.log_prob(a1_index),
            entropy_1=dist1.entropy(),
            reward=reward,
            batch_duration=batch_duration,
        )

    def _update_networks(
        self,
        buffer: list[Stage1StepRecord],
        returns: list[float],
    ) -> tuple[float, float]:
        """Update the stage-1 actor and critic from one episode buffer."""

        s1_batch = torch.stack([record.s1 for record in buffer])
        returns_tensor = torch.tensor(returns, dtype=torch.float32, device=self.device)
        log_probs_1 = torch.stack([record.log_prob_1 for record in buffer])
        entropies_1 = torch.stack([record.entropy_1 for record in buffer])

        v1_values = self.v1(s1_batch)
        loss_v1 = ((v1_values - returns_tensor.detach()) ** 2).mean()
        self.opt_v1.zero_grad()
        loss_v1.backward()
        nn.utils.clip_grad_norm_(self.v1.parameters(), self.config.max_grad_norm)
        self.opt_v1.step()

        with torch.no_grad():
            adv_1 = returns_tensor - self.v1(s1_batch)
            if self.config.normalize_advantages:
                adv_1 = RLCAPATrainer._normalize_advantages(adv_1)

        loss_pi1 = -(log_probs_1 * adv_1).mean() - self.config.entropy_coeff * entropies_1.mean()
        self.opt_pi1.zero_grad()
        loss_pi1.backward()
        nn.utils.clip_grad_norm_(self.pi1.parameters(), self.config.max_grad_norm)
        self.opt_pi1.step()
        return loss_pi1.item(), loss_v1.item()

    def _build_progress_payload(self, episode_log: Stage1EpisodeLog) -> dict[str, float | int | bool]:
        """Serialize one stage-1 episode into the shared progress schema."""

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
