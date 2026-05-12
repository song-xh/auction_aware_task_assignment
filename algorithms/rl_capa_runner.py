"""Unified RL-CAPA strategy wrapper for the root algorithm registry."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from capa.models import CAPAConfig
from experiments.deadline_disturbance import DEADLINE_DELAY_VALUES, DEADLINE_NOISE_VALUES
from experiments.seeding import build_environment_seed
from rl_capa.config import RLCAPAConfig, RLTrainingConfig
from rl_capa.evaluate import evaluate_rl_capa
from rl_capa.train import train_rl_capa

from .base import AlgorithmRunner


class RLCAPAAlgorithmRunner(AlgorithmRunner):
    """Train and evaluate RL-CAPA against one prepared Chengdu environment."""

    def __init__(
        self,
        min_batch_size: int = 10,
        max_batch_size: int = 20,
        batch_actions: Sequence[int] | None = None,
        step_seconds: int = 60,
        episodes: int = 10,
        lr_actor: float = 0.001,
        lr_critic: float = 0.001,
        discount_factor: float = 1.0,
        entropy_coeff: float = 0.01,
        entropy_start: float | None = None,
        entropy_end: float | None = None,
        entropy_decay_episodes: int | None = None,
        max_grad_norm: float = 0.5,
        normalize_advantages: bool = True,
        future_feature_window_seconds: int = 300,
        device: str | None = None,
        domain_randomize: bool = False,
        domain_randomize_delays: Sequence[float] | None = None,
        domain_randomize_noises: Sequence[float] | None = None,
        domain_randomize_seed: int = 0,
    ) -> None:
        """Store the RL-CAPA hyperparameters exposed through the unified runner.

        Args:
            min_batch_size: Lower bound of the `M_b` action space.
            max_batch_size: Upper bound of the `M_b` action space.
            batch_actions: Optional explicit batch-duration action set.
            step_seconds: Simulation time step used by the unified Chengdu environment.
            episodes: Joint-training episode count before evaluation.
            lr_actor: Actor learning rate for actor-critic training.
            lr_critic: Critic learning rate for actor-critic training.
            discount_factor: Gamma used for discounted returns.
            entropy_coeff: Entropy regularization coefficient.
            max_grad_norm: Gradient clipping threshold.
            normalize_advantages: Whether actor advantages are standardized during training.
            future_feature_window_seconds: True future window used by stage-1 features.
            device: Optional torch device override.
            domain_randomize: When True, sample a ``(delay_seconds,
                noise_percent)`` pair per episode and inject the disturbance
                onto the cloned environment before training begins.
            domain_randomize_delays: Optional override for the delay support.
                Defaults to ``(0,) + DEADLINE_DELAY_VALUES``.
            domain_randomize_noises: Optional override for the deadline-noise
                support. Defaults to ``(0,) + DEADLINE_NOISE_VALUES``.
            domain_randomize_seed: RNG seed for the domain-randomization
                sampler so training stays reproducible.
        """

        self._min_batch_size = min_batch_size
        self._max_batch_size = max_batch_size
        self._batch_actions = None if batch_actions is None else [int(value) for value in batch_actions]
        self._step_seconds = step_seconds
        self._episodes = episodes
        self._lr_actor = lr_actor
        self._lr_critic = lr_critic
        self._discount_factor = discount_factor
        self._entropy_coeff = entropy_coeff
        self._entropy_start = entropy_start
        self._entropy_end = entropy_end
        self._entropy_decay_episodes = entropy_decay_episodes
        self._max_grad_norm = max_grad_norm
        self._normalize_advantages = normalize_advantages
        self._future_feature_window_seconds = future_feature_window_seconds
        self._device = device
        self._domain_randomize = bool(domain_randomize)
        self._domain_randomize_delays = (
            None if domain_randomize_delays is None else [float(value) for value in domain_randomize_delays]
        )
        self._domain_randomize_noises = (
            None if domain_randomize_noises is None else [float(value) for value in domain_randomize_noises]
        )
        self._domain_randomize_seed = int(domain_randomize_seed)

    def run(
        self,
        environment: Any,
        output_dir: Path | None = None,
        progress_callback: Callable[[Mapping[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        """Train RL-CAPA from the provided Chengdu environment seed and evaluate it.

        Args:
            environment: Prepared unified Chengdu environment.
            output_dir: Optional directory for checkpoints and evaluation summaries.

        Returns:
            Normalized experiment summary with training metadata and evaluation metrics.
        """

        normalized_output_dir = Path("outputs/plots/rl_capa_run") if output_dir is None else output_dir
        normalized_output_dir.mkdir(parents=True, exist_ok=True)
        environment_seed = build_environment_seed(environment)
        effective_batch_actions = (
            self._batch_actions
            if self._batch_actions is not None
            else list(range(self._min_batch_size, self._max_batch_size + 1))
        )
        capa_config = CAPAConfig(batch_size=max(effective_batch_actions))
        rl_config = RLCAPAConfig(
            min_batch_size=self._min_batch_size,
            max_batch_size=self._max_batch_size,
            batch_actions=self._batch_actions,
            step_seconds=self._step_seconds,
            future_feature_window_seconds=self._future_feature_window_seconds,
        )
        training_config = RLTrainingConfig(
            episodes=self._episodes,
            discount_factor=self._discount_factor,
            lr_actor=self._lr_actor,
            lr_critic=self._lr_critic,
            entropy_coeff=self._entropy_coeff,
            entropy_start=self._entropy_start,
            entropy_end=self._entropy_end,
            entropy_decay_episodes=self._entropy_decay_episodes,
            max_grad_norm=self._max_grad_norm,
            normalize_advantages=self._normalize_advantages,
            device=self._device,
        )
        disturbance_sampler = self._build_disturbance_sampler()
        training_summary = train_rl_capa(
            environment_seed=environment_seed,
            capa_config=capa_config,
            rl_config=rl_config,
            training_config=training_config,
            output_dir=normalized_output_dir,
            progress_callback=progress_callback,
            disturbance_sampler=disturbance_sampler,
            disturbance_seed=self._domain_randomize_seed,
        )
        evaluation_summary = evaluate_rl_capa(
            environment_seed=environment_seed,
            capa_config=capa_config,
            rl_config=rl_config,
            checkpoint_dir=normalized_output_dir / "checkpoints",
            output_dir=normalized_output_dir / "eval",
            training_config=training_config,
        )
        summary = {
            "algorithm": "rl-capa",
            "training": training_summary,
            "evaluation": evaluation_summary,
            "metrics": evaluation_summary["metrics"],
            "plots": {
                "training": dict(training_summary.get("plots", {})),
                "evaluation": dict(evaluation_summary.get("plots", {})),
            },
        }
        with (normalized_output_dir / "summary.json").open("w", encoding="utf-8") as handle:
            json.dump(summary, handle, indent=2)
        return summary


    def _build_disturbance_sampler(self) -> Callable[[int, random.Random], Mapping[str, float]] | None:
        """Return a per-episode disturbance sampler when domain randomization is on.

        Delay support defaults to ``(0,) + DEADLINE_DELAY_VALUES`` and noise
        support defaults to ``(0,) + DEADLINE_NOISE_VALUES`` so the clean
        ``(0, 0)`` corner stays in the support and the policy still encounters
        clean episodes.
        """

        if not self._domain_randomize:
            return None
        delays = (
            tuple(self._domain_randomize_delays)
            if self._domain_randomize_delays is not None
            else (0.0, *(float(value) for value in DEADLINE_DELAY_VALUES))
        )
        noises = (
            tuple(self._domain_randomize_noises)
            if self._domain_randomize_noises is not None
            else (0.0, *(float(value) for value in DEADLINE_NOISE_VALUES))
        )

        def _sample(episode_index: int, rng: random.Random) -> Mapping[str, float]:
            del episode_index
            return {
                "delay_seconds": float(rng.choice(delays)),
                "noise_percent": float(rng.choice(noises)),
            }

        return _sample


def build_rl_capa_runner(
    min_batch_size: int = 10,
    max_batch_size: int = 20,
    batch_actions: Sequence[int] | None = None,
    step_seconds: int = 60,
    episodes: int = 10,
    lr_actor: float = 0.001,
    lr_critic: float = 0.001,
    discount_factor: float = 1.0,
    entropy_coeff: float = 0.01,
    entropy_start: float | None = None,
    entropy_end: float | None = None,
    entropy_decay_episodes: int | None = None,
    max_grad_norm: float = 0.5,
    normalize_advantages: bool = True,
    future_feature_window_seconds: int = 300,
    device: str | None = None,
    domain_randomize: bool = False,
    domain_randomize_delays: Sequence[float] | None = None,
    domain_randomize_noises: Sequence[float] | None = None,
    domain_randomize_seed: int = 0,
) -> RLCAPAAlgorithmRunner:
    """Build the unified RL-CAPA runner with explicit training hyperparameters."""

    return RLCAPAAlgorithmRunner(
        min_batch_size=min_batch_size,
        max_batch_size=max_batch_size,
        batch_actions=batch_actions,
        step_seconds=step_seconds,
        episodes=episodes,
        lr_actor=lr_actor,
        lr_critic=lr_critic,
        discount_factor=discount_factor,
        entropy_coeff=entropy_coeff,
        entropy_start=entropy_start,
        entropy_end=entropy_end,
        entropy_decay_episodes=entropy_decay_episodes,
        max_grad_norm=max_grad_norm,
        normalize_advantages=normalize_advantages,
        future_feature_window_seconds=future_feature_window_seconds,
        device=device,
        domain_randomize=domain_randomize,
        domain_randomize_delays=domain_randomize_delays,
        domain_randomize_noises=domain_randomize_noises,
        domain_randomize_seed=domain_randomize_seed,
    )
