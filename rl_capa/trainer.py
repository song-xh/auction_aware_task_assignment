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
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional

import numpy as np
import torch
import torch.nn as nn

from rl_capa.networks import (
    BatchSizeActor,
    BatchSizeQCritic,
    ConditionalValueCritic,
    CrossOrNotActor,
    StateValueCritic,
)
from rl_capa.state_builder import STAGE1_STATE_DIM, STAGE2_STATE_DIM, RunningNormalizer, aggregate_stage2_states
from rl_capa.utils import compute_discounted_returns, select_torch_device


@dataclass
class TrainingConfig:
    """Hyperparameters for RL-CAPA training (spec Section 10).

    Args:
        num_episodes: Total training episodes.
        discount_factor: Gamma for discounted returns.
        lr_actor: Learning rate for both actors.
        lr_critic: Learning rate for both critics.
        entropy_coeff: Base entropy bonus coefficient (used when entropy_start
            is None). Linear annealing between entropy_start and entropy_end
            over entropy_decay_episodes overrides this when entropy_start is set.
        entropy_start: Optional initial entropy coefficient for the linear schedule.
        entropy_end: Optional final entropy coefficient for the linear schedule.
        entropy_decay_episodes: Episodes over which entropy decays from
            entropy_start to entropy_end (clamped to num_episodes).
        max_grad_norm: Gradient clipping threshold.
        max_steps_per_episode: Safety limit on steps per episode.
        normalize_advantages: Whether to standardize detached advantages before actor updates.
    """

    num_episodes: int = 500
    discount_factor: float = 1.0
    lr_actor: float = 0.001
    lr_critic: float = 0.001
    entropy_coeff: float = 0.01
    entropy_start: float | None = None
    entropy_end: float | None = None
    entropy_decay_episodes: int | None = None
    max_grad_norm: float = 0.5
    max_steps_per_episode: int = 500
    normalize_advantages: bool = True
    device: str | None = None


@dataclass
class StepRecord:
    """One step's data in the episode buffer.

    Args:
        s1: First-stage state tensor (6,).
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
        entropy_pi1: Mean first-stage policy entropy across episode steps.
        entropy_pi2: Parcel-normalized second-stage policy entropy across the episode.
        mean_batch_size: Mean selected batch duration in seconds.
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
    entropy_pi1: float = 0.0
    entropy_pi2: float = 0.0
    mean_batch_size: float = 0.0
    truncated: bool = False


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
        device: str | None = None,
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
        self.device = select_torch_device(config.device if device is None else device)

        # 4 networks (spec Section 7; Q1 replaces V1 to avoid V1==V2 target
        # collapse described in docs/review_0507.md §3.2).
        self.pi1 = BatchSizeActor(
            state_dim=STAGE1_STATE_DIM, num_actions=num_batch_actions, hidden_dim=128
        ).to(self.device)
        self.pi2 = CrossOrNotActor(state_dim=STAGE2_STATE_DIM, hidden_dim=128).to(self.device)
        self.q1 = BatchSizeQCritic(
            state_dim=STAGE1_STATE_DIM, num_actions=num_batch_actions, hidden_dim=128
        ).to(self.device)
        self.v1 = StateValueCritic(state_dim=STAGE1_STATE_DIM, hidden_dim=128).to(self.device)
        self.v2 = ConditionalValueCritic(state_dim=STAGE2_STATE_DIM, hidden_dim=128).to(self.device)

        # 4 independent optimizers (spec Section 6.4)
        self.opt_pi1 = torch.optim.Adam(self.pi1.parameters(), lr=config.lr_actor)
        self.opt_pi2 = torch.optim.Adam(self.pi2.parameters(), lr=config.lr_actor)
        self.opt_q1 = torch.optim.Adam(self.q1.parameters(), lr=config.lr_critic)
        self.opt_v1 = torch.optim.Adam(self.v1.parameters(), lr=config.lr_critic)
        self.opt_v2 = torch.optim.Adam(self.v2.parameters(), lr=config.lr_critic)

        # Running normalizers for feature vectors
        self.norm_s1 = RunningNormalizer(dim=STAGE1_STATE_DIM)
        self.norm_s2 = RunningNormalizer(dim=STAGE2_STATE_DIM)

        # Batch action values for index-to-duration mapping
        self._batch_action_values: List[int] = []

        # Training history
        self.history: List[EpisodeLog] = []

    def train(
        self,
        batch_action_values: List[int],
        progress_callback: Callable[[Mapping[str, float | int | bool]], None] | None = None,
    ) -> List[EpisodeLog]:
        """Run the full training loop.

        Args:
            batch_action_values: Ordered list of batch durations for A_b.
            progress_callback: Optional structured progress sink invoked once per episode.

        Returns:
            List of per-episode logs.
        """
        if len(batch_action_values) != self.pi1.net[-1].out_features:
            raise ValueError(
                f"batch_action_values size {len(batch_action_values)} does not match "
                f"pi1 output dim {self.pi1.net[-1].out_features}."
            )
        self._batch_action_values = list(batch_action_values)
        self.history = []

        for episode_idx in range(self.config.num_episodes):
            log = self._run_episode(episode_idx)
            self.history.append(log)
            if progress_callback is not None:
                progress_callback(
                    self._build_progress_payload(
                        episode_log=log,
                        total_episodes=self.config.num_episodes,
                    )
                )

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
            self.env.finalize_episode()
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

        # Update networks (entropy coefficient annealed per episode)
        entropy_coeff = self._current_entropy_coeff(episode_idx)
        loss_pi1, loss_pi2, loss_v1, loss_v2 = self._update_networks(
            episode_buffer, returns, entropy_coeff=entropy_coeff
        )

        self.env.finalize_episode()

        total_reward = sum(r.reward for r in episode_buffer)
        batch_sizes = [r.batch_duration for r in episode_buffer]
        total_cross = sum(r.num_cross for r in episode_buffer)
        total_unassigned = sum(r.num_unassigned for r in episode_buffer)
        cross_rate = total_cross / max(total_unassigned, 1)
        entropy_pi1 = float(np.mean([r.entropy_1.detach().item() for r in episode_buffer]))
        entropy_pi2 = float(
            sum(r.entropy_2.detach().item() for r in episode_buffer)
            / max(total_unassigned, 1)
        )
        mean_batch_size = float(np.mean(batch_sizes)) if batch_sizes else 0.0
        truncated = not self.env.is_done()
        return EpisodeLog(
            episode=episode_idx,
            total_reward=total_reward,
            loss_pi1=loss_pi1,
            loss_pi2=loss_pi2,
            loss_v1=loss_v1,
            loss_v2=loss_v2,
            steps=step,
            assignments=len(self.env.delivered_parcels()),
            batch_sizes=batch_sizes,
            cross_rate=cross_rate,
            entropy_pi1=entropy_pi1,
            entropy_pi2=entropy_pi2,
            mean_batch_size=mean_batch_size,
            truncated=truncated,
        )

    def _build_progress_payload(
        self,
        episode_log: EpisodeLog,
        total_episodes: int,
    ) -> dict[str, float | int | bool]:
        """Serialize one episode log into a compact structured progress payload."""

        return {
            "episode": episode_log.episode + 1,
            "total_episodes": total_episodes,
            "total_reward": episode_log.total_reward,
            "steps": episode_log.steps,
            "assignments": episode_log.assignments,
            "avg_batch_size": episode_log.mean_batch_size,
            "cross_rate": episode_log.cross_rate,
            "entropy_pi1": episode_log.entropy_pi1,
            "entropy_pi2": episode_log.entropy_pi2,
            "truncated": episode_log.truncated,
        }

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

        # === Stage 2: per-parcel local-or-cross ===
        batch_parcels = self.env.current_eligible_parcels()
        s2_list = self.env.get_stage2_states(batch_parcels)

        num_unassigned = len(batch_parcels)
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
                for p, a in zip(batch_parcels, actions_2)
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
            s2_agg_tensor = torch.zeros(STAGE2_STATE_DIM, device=self.device)

        # Apply local/cross decisions -> direct local + DAPA, returns R_t
        reward = self.env.apply_stage2_decisions(decisions)

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
        return compute_discounted_returns(
            rewards=[record.reward for record in buffer],
            discount_factor=self.config.discount_factor,
        )

    def _current_entropy_coeff(self, episode_idx: int) -> float:
        """Linear-anneal the entropy bonus across the configured schedule.

        Falls back to ``config.entropy_coeff`` when ``entropy_start`` is None.
        """

        start = self.config.entropy_start
        end = self.config.entropy_end
        decay = self.config.entropy_decay_episodes
        if start is None:
            return float(self.config.entropy_coeff)
        if end is None:
            end = float(self.config.entropy_coeff)
        if decay is None or decay <= 0:
            decay = max(1, self.config.num_episodes)
        progress = min(1.0, episode_idx / max(1, decay))
        return float(start + (end - start) * progress)

    def _update_networks(
        self,
        buffer: List[StepRecord],
        returns: List[float],
        entropy_coeff: float | None = None,
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
        if entropy_coeff is None:
            entropy_coeff = float(self.config.entropy_coeff)
        # Stack episode data
        s1_batch = torch.stack([r.s1 for r in buffer])
        s2_agg_batch = torch.stack([r.s2_agg for r in buffer])
        returns_tensor = torch.tensor(returns, dtype=torch.float32, device=self.device)
        # Per-step rewards drive pi2's local advantage so pi2 only sees its own
        # batch's outcome (review §3.5).
        rewards_tensor = torch.tensor(
            [r.reward for r in buffer], dtype=torch.float32, device=self.device
        )
        action_indices = torch.tensor(
            [r.a1_index for r in buffer], dtype=torch.long, device=self.device
        )
        log_probs_1 = torch.stack([r.log_prob_1 for r in buffer])
        log_probs_2 = torch.stack([r.log_prob_2 for r in buffer])
        entropies_1 = torch.stack([r.entropy_1 for r in buffer])
        entropies_2 = torch.stack([r.entropy_2 for r in buffer])

        # --- Q1 critic update (action-value regression to R_hat) ---
        q1_all = self.q1(s1_batch)  # (T, |A_b|)
        q1_taken = q1_all.gather(1, action_indices.unsqueeze(-1)).squeeze(-1)
        loss_q1 = ((q1_taken - returns_tensor.detach()) ** 2).mean()
        self.opt_q1.zero_grad()
        loss_q1.backward()
        nn.utils.clip_grad_norm_(self.q1.parameters(), self.config.max_grad_norm)
        self.opt_q1.step()

        # --- V1 baseline update (value regression for monitoring + variance) ---
        v1_values = self.v1(s1_batch)
        loss_v1 = ((v1_values - returns_tensor.detach()) ** 2).mean()
        self.opt_v1.zero_grad()
        loss_v1.backward()
        nn.utils.clip_grad_norm_(self.v1.parameters(), self.config.max_grad_norm)
        self.opt_v1.step()

        # --- V2 critic update (per-step reward target, decoupled from pi1) ---
        v2_values = self.v2(s2_agg_batch)
        loss_v2 = ((v2_values - rewards_tensor.detach()) ** 2).mean()
        self.opt_v2.zero_grad()
        loss_v2.backward()
        nn.utils.clip_grad_norm_(self.v2.parameters(), self.config.max_grad_norm)
        self.opt_v2.step()

        # --- Advantages (detached) ---
        with torch.no_grad():
            q1_detached = self.q1(s1_batch)
            pi1_probs = self.pi1(s1_batch).probs              # (T, |A_b|)
            q1_baseline = (pi1_probs * q1_detached).sum(dim=-1)
            q1_taken_detached = q1_detached.gather(
                1, action_indices.unsqueeze(-1)
            ).squeeze(-1)
            # A1 = Q1(s, a) - E_{a' ~ pi1}[Q1(s, a')] (counterfactual advantage)
            adv_1 = q1_taken_detached - q1_baseline
            # A2 = r_t - V2(s2_agg): pi2 credit limited to its batch outcome.
            v2_detached = self.v2(s2_agg_batch)
            adv_2 = rewards_tensor - v2_detached
            if self.config.normalize_advantages:
                adv_1 = self._normalize_advantages(adv_1)
                adv_2 = self._normalize_advantages(adv_2)

        # --- Actor 1 update ---
        loss_pi1 = -(log_probs_1 * adv_1).mean() - entropy_coeff * entropies_1.mean()
        self.opt_pi1.zero_grad()
        loss_pi1.backward()
        nn.utils.clip_grad_norm_(self.pi1.parameters(), self.config.max_grad_norm)
        self.opt_pi1.step()

        # --- Actor 2 update ---
        loss_pi2 = -(log_probs_2 * adv_2).mean() - entropy_coeff * entropies_2.mean()
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

    @staticmethod
    def _normalize_advantages(advantages: torch.Tensor, epsilon: float = 1e-8) -> torch.Tensor:
        """Standardize one detached advantage vector for stable actor updates.

        When variance collapses (e.g., pi1 deterministic), fall back to the
        mean-centered raw advantage instead of zeroing it out, so the actor
        still receives any residual signal. See docs/review_0507.md §3.4.

        Args:
            advantages: One-dimensional tensor of detached advantage values.
            epsilon: Minimum standard deviation used for numerical stability.

        Returns:
            Mean-centered advantages, scaled by std when std > epsilon.
        """

        centered = advantages - advantages.mean()
        std = centered.std(unbiased=False)
        if std <= epsilon:
            return centered
        return centered / (std + epsilon)

    def save_checkpoint(self, output_dir: Path) -> None:
        """Persist model weights and normalizer state for later evaluation.

        Args:
            output_dir: Directory receiving the trainer checkpoint files.
        """

        output_dir.mkdir(parents=True, exist_ok=True)
        torch.save(self.pi1.state_dict(), output_dir / "pi1.pt")
        torch.save(self.pi2.state_dict(), output_dir / "pi2.pt")
        torch.save(self.q1.state_dict(), output_dir / "q1.pt")
        torch.save(self.v1.state_dict(), output_dir / "v1.pt")
        torch.save(self.v2.state_dict(), output_dir / "v2.pt")
        torch.save(
            {
                "norm_s1": self._serialize_normalizer(self.norm_s1),
                "norm_s2": self._serialize_normalizer(self.norm_s2),
            },
            output_dir / "normalizers.pt",
        )

    @classmethod
    def load_checkpoint(
        cls,
        env: object,
        config: TrainingConfig,
        num_batch_actions: int,
        checkpoint_dir: Path,
    ) -> "RLCAPATrainer":
        """Restore one trainer from persisted actor-critic checkpoints.

        Args:
            env: Evaluation environment instance.
            config: Training configuration used to rebuild the trainer.
            num_batch_actions: Size of the discrete batch-size action space.
            checkpoint_dir: Directory containing saved network and normalizer state.

        Returns:
            Restored actor-critic trainer ready for evaluation.
        """

        trainer = cls(
            env=env,
            config=config,
            num_batch_actions=num_batch_actions,
            device=config.device,
        )
        trainer.pi1.load_state_dict(torch.load(checkpoint_dir / "pi1.pt", map_location=trainer.device))
        trainer.pi2.load_state_dict(torch.load(checkpoint_dir / "pi2.pt", map_location=trainer.device))
        q1_path = checkpoint_dir / "q1.pt"
        if q1_path.exists():
            trainer.q1.load_state_dict(torch.load(q1_path, map_location=trainer.device))
        trainer.v1.load_state_dict(torch.load(checkpoint_dir / "v1.pt", map_location=trainer.device))
        trainer.v2.load_state_dict(torch.load(checkpoint_dir / "v2.pt", map_location=trainer.device))
        normalizers = torch.load(checkpoint_dir / "normalizers.pt", map_location="cpu")
        trainer._restore_normalizer(trainer.norm_s1, normalizers["norm_s1"])
        trainer._restore_normalizer(trainer.norm_s2, normalizers["norm_s2"])
        return trainer

    @staticmethod
    def _serialize_normalizer(normalizer: RunningNormalizer) -> dict[str, Any]:
        """Serialize one running normalizer into checkpoint-friendly tensors."""

        return {
            "dim": normalizer.dim,
            "epsilon": normalizer.epsilon,
            "count": normalizer.count,
            "mean": torch.as_tensor(normalizer.mean, dtype=torch.float64),
            "var": torch.as_tensor(normalizer.var, dtype=torch.float64),
            "m2": torch.as_tensor(normalizer._m2, dtype=torch.float64),
        }

    @staticmethod
    def _restore_normalizer(normalizer: RunningNormalizer, payload: Dict[str, Any]) -> None:
        """Restore one running normalizer from serialized checkpoint data."""

        normalizer.count = int(payload["count"])
        normalizer.mean = np.asarray(payload["mean"].cpu(), dtype=np.float64)
        normalizer.var = np.asarray(payload["var"].cpu(), dtype=np.float64)
        normalizer._m2 = np.asarray(payload["m2"].cpu(), dtype=np.float64)
