"""Actor-critic RL-CAPA training entrypoint."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import torch

from capa.models import CAPAConfig
from experiments.seeding import ChengduEnvironmentSeed

from .config import RLCAPAConfig, RLTrainingConfig
from .env import RLCAPAEnv
from .trainer import RLCAPATrainer, TrainingConfig


def train_rl_capa(
    environment_seed: ChengduEnvironmentSeed,
    capa_config: CAPAConfig,
    rl_config: RLCAPAConfig,
    training_config: RLTrainingConfig,
    output_dir: Path,
) -> dict[str, Any]:
    """Train the hierarchical actor-critic RL-CAPA policy.

    Args:
        environment_seed: Immutable Chengdu environment seed.
        capa_config: Shared CAPA configuration.
        rl_config: RL environment configuration.
        training_config: Actor-critic hyperparameters.
        output_dir: Directory for checkpoints and training summary files.

    Returns:
        JSON-serializable training summary.
    """

    output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_dir = output_dir / "checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    env = RLCAPAEnv(
        environment_seed=environment_seed,
        capa_config=capa_config,
        rl_config=rl_config,
    )
    trainer = RLCAPATrainer(
        env=env,
        config=TrainingConfig(
            num_episodes=training_config.episodes,
            discount_factor=training_config.discount_factor,
            lr_actor=training_config.lr_actor,
            lr_critic=training_config.lr_critic,
            entropy_coeff=training_config.entropy_coeff,
            max_grad_norm=training_config.max_grad_norm,
            max_steps_per_episode=training_config.max_steps_per_episode,
            device=training_config.device,
        ),
        num_batch_actions=len(rl_config.batch_action_values()),
    )
    history = trainer.train(batch_action_values=rl_config.batch_action_values())
    trainer.save_checkpoint(checkpoint_dir)

    summary = {
        "episode_returns": [log.total_reward for log in history],
        "loss_pi1": [log.loss_pi1 for log in history],
        "loss_pi2": [log.loss_pi2 for log in history],
        "loss_v1": [log.loss_v1 for log in history],
        "loss_v2": [log.loss_v2 for log in history],
        "cross_rate": [log.cross_rate for log in history],
        "batch_size_sequences": [list(log.batch_sizes) for log in history],
        "checkpoint_dir": str(checkpoint_dir),
        "device": str(trainer.device),
    }
    with (output_dir / "training_summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
    return summary
