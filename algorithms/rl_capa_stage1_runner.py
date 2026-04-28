"""Unified runner for the stage-1-only RL-CAPA ablation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from capa.models import CAPAConfig
from experiments.seeding import build_environment_seed
from rl_capa.config import RLCAPAConfig, RLTrainingConfig
from rl_capa.train_stage1 import train_stage1_rl_capa

from .base import AlgorithmRunner


class RLCAPAStage1AlgorithmRunner(AlgorithmRunner):
    """Train the batch-size-only RL-CAPA ablation."""

    def __init__(
        self,
        min_batch_size: int = 10,
        max_batch_size: int = 20,
        batch_actions: Sequence[int] | None = None,
        step_seconds: int = 60,
        episodes: int = 10,
        lr_actor: float = 0.001,
        lr_critic: float = 0.001,
        discount_factor: float = 0.9,
        entropy_coeff: float = 0.01,
        max_grad_norm: float = 0.5,
        normalize_advantages: bool = True,
        future_feature_window_seconds: int = 300,
        device: str | None = None,
    ) -> None:
        """Store stage-1 ablation hyperparameters."""

        self._min_batch_size = min_batch_size
        self._max_batch_size = max_batch_size
        self._batch_actions = None if batch_actions is None else [int(value) for value in batch_actions]
        self._step_seconds = step_seconds
        self._episodes = episodes
        self._lr_actor = lr_actor
        self._lr_critic = lr_critic
        self._discount_factor = discount_factor
        self._entropy_coeff = entropy_coeff
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
        """Train the ablation and return a normalized summary."""

        normalized_output_dir = Path("outputs/plots/rl_capa_stage1") if output_dir is None else output_dir
        normalized_output_dir.mkdir(parents=True, exist_ok=True)
        effective_batch_actions = (
            self._batch_actions
            if self._batch_actions is not None
            else list(range(self._min_batch_size, self._max_batch_size + 1))
        )
        environment_seed = build_environment_seed(environment)
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
            max_grad_norm=self._max_grad_norm,
            normalize_advantages=self._normalize_advantages,
            device=self._device,
        )
        training_summary = train_stage1_rl_capa(
            environment_seed=environment_seed,
            capa_config=capa_config,
            rl_config=rl_config,
            training_config=training_config,
            output_dir=normalized_output_dir,
            progress_callback=progress_callback,
        )
        summary = {
            "algorithm": "rl-capa-stage1",
            "training": training_summary,
            "metrics": {},
            "plots": {"training": dict(training_summary.get("plots", {}))},
        }
        with (normalized_output_dir / "summary.json").open("w", encoding="utf-8") as handle:
            json.dump(summary, handle, indent=2)
        return summary


def build_rl_capa_stage1_runner(
    min_batch_size: int = 10,
    max_batch_size: int = 20,
    batch_actions: Sequence[int] | None = None,
    step_seconds: int = 60,
    episodes: int = 10,
    lr_actor: float = 0.001,
    lr_critic: float = 0.001,
    discount_factor: float = 0.9,
    entropy_coeff: float = 0.01,
    max_grad_norm: float = 0.5,
    normalize_advantages: bool = True,
    future_feature_window_seconds: int = 300,
    device: str | None = None,
) -> RLCAPAStage1AlgorithmRunner:
    """Build a stage-1-only RL-CAPA ablation runner."""

    return RLCAPAStage1AlgorithmRunner(
        min_batch_size=min_batch_size,
        max_batch_size=max_batch_size,
        batch_actions=batch_actions,
        step_seconds=step_seconds,
        episodes=episodes,
        lr_actor=lr_actor,
        lr_critic=lr_critic,
        discount_factor=discount_factor,
        entropy_coeff=entropy_coeff,
        max_grad_norm=max_grad_norm,
        normalize_advantages=normalize_advantages,
        future_feature_window_seconds=future_feature_window_seconds,
        device=device,
    )
