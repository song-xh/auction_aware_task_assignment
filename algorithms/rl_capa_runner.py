"""Unified RL-CAPA strategy wrapper for the root algorithm registry."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Mapping

from capa.models import CAPAConfig
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
        step_seconds: int = 60,
        episodes: int = 10,
        lr_actor: float = 0.001,
        lr_critic: float = 0.001,
        discount_factor: float = 0.9,
        entropy_coeff: float = 0.01,
        max_grad_norm: float = 0.5,
        device: str | None = None,
    ) -> None:
        """Store the RL-CAPA hyperparameters exposed through the unified runner.

        Args:
            min_batch_size: Lower bound of the `M_b` action space.
            max_batch_size: Upper bound of the `M_b` action space.
            step_seconds: Simulation time step used by the unified Chengdu environment.
            episodes: Joint-training episode count before evaluation.
            lr_actor: Actor learning rate for actor-critic training.
            lr_critic: Critic learning rate for actor-critic training.
            discount_factor: Gamma used for discounted returns.
            entropy_coeff: Entropy regularization coefficient.
            max_grad_norm: Gradient clipping threshold.
            device: Optional torch device override.
        """

        self._min_batch_size = min_batch_size
        self._max_batch_size = max_batch_size
        self._step_seconds = step_seconds
        self._episodes = episodes
        self._lr_actor = lr_actor
        self._lr_critic = lr_critic
        self._discount_factor = discount_factor
        self._entropy_coeff = entropy_coeff
        self._max_grad_norm = max_grad_norm
        self._device = device

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

        del progress_callback
        normalized_output_dir = Path("outputs/plots/rl_capa_run") if output_dir is None else output_dir
        normalized_output_dir.mkdir(parents=True, exist_ok=True)
        environment_seed = build_environment_seed(environment)
        capa_config = CAPAConfig(batch_size=self._max_batch_size)
        rl_config = RLCAPAConfig(
            min_batch_size=self._min_batch_size,
            max_batch_size=self._max_batch_size,
            step_seconds=self._step_seconds,
        )
        training_config = RLTrainingConfig(episodes=self._episodes)
        training_summary = train_rl_capa(
            environment_seed=environment_seed,
            capa_config=capa_config,
            rl_config=rl_config,
            training_config=training_config,
            output_dir=normalized_output_dir,
        )
        evaluation_summary = evaluate_rl_capa(
            environment_seed=environment_seed,
            capa_config=capa_config,
            rl_config=rl_config,
            checkpoint_dir=normalized_output_dir / "checkpoints",
            output_dir=normalized_output_dir / "eval",
        )
        summary = {
            "algorithm": "rl-capa",
            "training": training_summary,
            "metrics": evaluation_summary["metrics"],
        }
        with (normalized_output_dir / "summary.json").open("w", encoding="utf-8") as handle:
            json.dump(summary, handle, indent=2)
        return summary


def build_rl_capa_runner(
    min_batch_size: int = 10,
    max_batch_size: int = 20,
    step_seconds: int = 60,
    episodes: int = 10,
    lr_actor: float = 0.001,
    lr_critic: float = 0.001,
    discount_factor: float = 0.9,
    entropy_coeff: float = 0.01,
    max_grad_norm: float = 0.5,
    device: str | None = None,
) -> RLCAPAAlgorithmRunner:
    """Build the unified RL-CAPA runner with explicit training hyperparameters."""

    return RLCAPAAlgorithmRunner(
        min_batch_size=min_batch_size,
        max_batch_size=max_batch_size,
        step_seconds=step_seconds,
        episodes=episodes,
        lr_actor=lr_actor,
        lr_critic=lr_critic,
        discount_factor=discount_factor,
        entropy_coeff=entropy_coeff,
        max_grad_norm=max_grad_norm,
        device=device,
    )
