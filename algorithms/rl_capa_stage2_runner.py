"""Unified runner for the fixed-batch stage-2-only RL-CAPA ablation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Mapping

from capa.models import CAPAConfig
from experiments.seeding import build_environment_seed
from rl_capa.config import RLCAPAConfig, RLTrainingConfig
from rl_capa.train_stage2 import train_stage2_rl_capa

from .base import AlgorithmRunner


class RLCAPAStage2AlgorithmRunner(AlgorithmRunner):
    """Train the fixed-batch parcel-level RL-CAPA ablation."""

    def __init__(
        self,
        fixed_batch_size: int = 30,
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
        """Store stage-2 ablation hyperparameters."""

        self._fixed_batch_size = fixed_batch_size
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

        normalized_output_dir = Path("outputs/plots/rl_capa_stage2") if output_dir is None else output_dir
        normalized_output_dir.mkdir(parents=True, exist_ok=True)
        environment_seed = build_environment_seed(environment)
        capa_config = CAPAConfig(batch_size=self._fixed_batch_size)
        rl_config = RLCAPAConfig(
            min_batch_size=self._fixed_batch_size,
            max_batch_size=self._fixed_batch_size,
            batch_actions=[self._fixed_batch_size],
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
        training_summary = train_stage2_rl_capa(
            environment_seed=environment_seed,
            capa_config=capa_config,
            rl_config=rl_config,
            training_config=training_config,
            fixed_batch_size=self._fixed_batch_size,
            output_dir=normalized_output_dir,
            progress_callback=progress_callback,
        )
        summary = {
            "algorithm": "rl-capa-stage2",
            "training": training_summary,
            "metrics": {},
            "plots": {"training": dict(training_summary.get("plots", {}))},
        }
        with (normalized_output_dir / "summary.json").open("w", encoding="utf-8") as handle:
            json.dump(summary, handle, indent=2)
        return summary


def build_rl_capa_stage2_runner(
    fixed_batch_size: int = 30,
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
) -> RLCAPAStage2AlgorithmRunner:
    """Build a fixed-batch stage-2-only RL-CAPA ablation runner."""

    return RLCAPAStage2AlgorithmRunner(
        fixed_batch_size=fixed_batch_size,
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
