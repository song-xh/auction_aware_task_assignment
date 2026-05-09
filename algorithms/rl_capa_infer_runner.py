"""Unified RL-CAPA inference-only runner for checkpoint evaluation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from capa.models import CAPAConfig
from experiments.seeding import build_environment_seed
from rl_capa.config import RLCAPAConfig, RLTrainingConfig
from rl_capa.evaluate import evaluate_rl_capa

from .base import AlgorithmRunner


class RLCAPAInferenceAlgorithmRunner(AlgorithmRunner):
    """Run checkpointed RL-CAPA inference against one prepared environment."""

    def __init__(
        self,
        checkpoint_dir: str | Path | None,
        min_batch_size: int = 10,
        max_batch_size: int = 20,
        batch_actions: Sequence[int] | None = None,
        step_seconds: int = 60,
        episodes: int = 500,
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
    ) -> None:
        """Store the checkpoint path and RL config required for inference.

        Args:
            checkpoint_dir: Directory containing saved RL-CAPA checkpoint files.
            min_batch_size: Lower bound of the batch-size action space.
            max_batch_size: Upper bound of the batch-size action space.
            batch_actions: Optional explicit batch-duration action set.
            step_seconds: Simulation time step in seconds.
            episodes: Original training episode count, used to rebuild config only.
            lr_actor: Original actor learning rate, used to rebuild config only.
            lr_critic: Original critic learning rate, used to rebuild config only.
            discount_factor: Discount factor used during training.
            entropy_coeff: Base entropy regularization coefficient.
            entropy_start: Optional initial entropy coefficient.
            entropy_end: Optional final entropy coefficient.
            entropy_decay_episodes: Optional entropy schedule length.
            max_grad_norm: Gradient clipping threshold.
            normalize_advantages: Whether training standardized actor advantages.
            future_feature_window_seconds: True future feature window used by stage 1.
            device: Optional torch device override.
        """

        self._checkpoint_dir = None if checkpoint_dir is None else Path(checkpoint_dir)
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

    def run(
        self,
        environment: Any,
        output_dir: Path | None = None,
        progress_callback: Callable[[Mapping[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        """Load a trained RL-CAPA checkpoint and run inference only.

        Args:
            environment: Prepared unified Chengdu environment.
            output_dir: Optional directory for evaluation outputs.
            progress_callback: Unused for inference-only evaluation.

        Returns:
            Normalized checkpoint-evaluation summary.
        """

        del progress_callback
        if self._checkpoint_dir is None:
            raise ValueError("rl-capa-infer requires a checkpoint_dir.")
        if not self._checkpoint_dir.exists():
            raise FileNotFoundError(f"RL-CAPA checkpoint directory does not exist: {self._checkpoint_dir}")

        normalized_output_dir = Path("outputs/plots/rl_capa_infer_run") if output_dir is None else output_dir
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
        evaluation_summary = evaluate_rl_capa(
            environment_seed=environment_seed,
            capa_config=capa_config,
            rl_config=rl_config,
            checkpoint_dir=self._checkpoint_dir,
            output_dir=normalized_output_dir / "eval",
            training_config=training_config,
        )
        summary = {
            "algorithm": "rl-capa-infer",
            "checkpoint_dir": str(self._checkpoint_dir),
            "evaluation": evaluation_summary,
            "metrics": evaluation_summary["metrics"],
            "plots": {
                "evaluation": dict(evaluation_summary.get("plots", {})),
            },
            "config": {
                "batch_actions": list(rl_config.batch_action_values()),
                "step_seconds": self._step_seconds,
                "future_feature_window_seconds": self._future_feature_window_seconds,
                "discount_factor": self._discount_factor,
            },
        }
        with (normalized_output_dir / "summary.json").open("w", encoding="utf-8") as handle:
            json.dump(summary, handle, indent=2)
        return summary


def build_rl_capa_infer_runner(
    checkpoint_dir: str | Path | None,
    min_batch_size: int = 10,
    max_batch_size: int = 20,
    batch_actions: Sequence[int] | None = None,
    step_seconds: int = 60,
    episodes: int = 500,
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
) -> RLCAPAInferenceAlgorithmRunner:
    """Build one inference-only RL-CAPA runner."""

    return RLCAPAInferenceAlgorithmRunner(
        checkpoint_dir=checkpoint_dir,
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
    )
