"""Unified runner for combined RL-CAPA ablation training curves."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from capa.models import CAPAConfig
from experiments.seeding import build_environment_seed
from rl_capa.ablation_compare import plot_reward_comparison
from rl_capa.config import RLCAPAConfig, RLTrainingConfig
from rl_capa.train import train_rl_capa
from rl_capa.train_stage1 import train_stage1_rl_capa
from rl_capa.train_stage2 import train_stage2_rl_capa

from .base import AlgorithmRunner


class RLCAPAAblationAlgorithmRunner(AlgorithmRunner):
    """Train full RL-CAPA plus two ablations on one environment seed."""

    def __init__(
        self,
        min_batch_size: int = 10,
        max_batch_size: int = 20,
        batch_actions: Sequence[int] | None = None,
        fixed_batch_size: int = 30,
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
    ) -> None:
        """Store combined ablation hyperparameters."""

        self._min_batch_size = min_batch_size
        self._max_batch_size = max_batch_size
        self._batch_actions = None if batch_actions is None else [int(value) for value in batch_actions]
        self._fixed_batch_size = fixed_batch_size
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
        """Train full and ablation variants, then plot reward histories."""

        del progress_callback
        normalized_output_dir = Path("outputs/plots/rl_capa_ablation") if output_dir is None else output_dir
        normalized_output_dir.mkdir(parents=True, exist_ok=True)
        environment_seed = build_environment_seed(environment)
        effective_batch_actions = (
            self._batch_actions
            if self._batch_actions is not None
            else list(range(self._min_batch_size, self._max_batch_size + 1))
        )
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
        full_summary = train_rl_capa(
            environment_seed=environment_seed,
            capa_config=CAPAConfig(batch_size=max(effective_batch_actions)),
            rl_config=rl_config,
            training_config=training_config,
            output_dir=normalized_output_dir / "rl-capa",
        )
        stage1_summary = train_stage1_rl_capa(
            environment_seed=environment_seed,
            capa_config=CAPAConfig(batch_size=max(effective_batch_actions)),
            rl_config=rl_config,
            training_config=training_config,
            output_dir=normalized_output_dir / "rl-capa-stage1",
        )
        stage2_rl_config = RLCAPAConfig(
            min_batch_size=self._fixed_batch_size,
            max_batch_size=self._fixed_batch_size,
            batch_actions=[self._fixed_batch_size],
            step_seconds=self._step_seconds,
            future_feature_window_seconds=self._future_feature_window_seconds,
        )
        stage2_summary = train_stage2_rl_capa(
            environment_seed=environment_seed,
            capa_config=CAPAConfig(batch_size=self._fixed_batch_size),
            rl_config=stage2_rl_config,
            training_config=training_config,
            fixed_batch_size=self._fixed_batch_size,
            output_dir=normalized_output_dir / "rl-capa-stage2",
        )
        reward_plot = plot_reward_comparison(
            reward_histories={
                "rl-capa": full_summary["episode_returns"],
                "rl-capa-stage1": stage1_summary["episode_returns"],
                "rl-capa-stage2": stage2_summary["episode_returns"],
            },
            output_path=normalized_output_dir / "reward_comparison.png",
        )
        summary = {
            "algorithm": "rl-capa-ablation",
            "training": {
                "rl-capa": full_summary,
                "rl-capa-stage1": stage1_summary,
                "rl-capa-stage2": stage2_summary,
            },
            "metrics": {},
            "plots": {
                "reward_comparison": str(reward_plot),
            },
        }
        with (normalized_output_dir / "summary.json").open("w", encoding="utf-8") as handle:
            json.dump(summary, handle, indent=2)
        return summary


def build_rl_capa_ablation_runner(
    min_batch_size: int = 10,
    max_batch_size: int = 20,
    batch_actions: Sequence[int] | None = None,
    fixed_batch_size: int = 30,
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
) -> RLCAPAAblationAlgorithmRunner:
    """Build a combined RL-CAPA ablation runner."""

    return RLCAPAAblationAlgorithmRunner(
        min_batch_size=min_batch_size,
        max_batch_size=max_batch_size,
        batch_actions=batch_actions,
        fixed_batch_size=fixed_batch_size,
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
