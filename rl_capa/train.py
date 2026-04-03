"""Joint DDQN training loop for RL-CAPA."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

import numpy as np
import torch

from capa.models import CAPAConfig
from experiments.seeding import ChengduEnvironmentSeed

from .config import RLCAPAConfig, RLTrainingConfig
from .ddqn import DDQNAgent, ReplayBuffer
from .env import RLCAPAEnvironment


def train_rl_capa(
    environment_seed: ChengduEnvironmentSeed,
    capa_config: CAPAConfig,
    rl_config: RLCAPAConfig,
    training_config: RLTrainingConfig,
    output_dir: Path,
) -> dict[str, Any]:
    """Train the coupled RL-CAPA batch and parcel DDQN agents.

    Args:
        environment_seed: Immutable Chengdu episode seed.
        capa_config: Shared CAPA configuration reused inside the environment.
        rl_config: RL-CAPA action-space configuration.
        training_config: DDQN hyperparameters.
        output_dir: Directory for checkpoints and training summary files.

    Returns:
        Training summary with episode returns and optimization statistics.
    """

    _set_random_seed(training_config.random_seed)
    output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_dir = output_dir / "checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    environment = RLCAPAEnvironment(
        environment_seed=environment_seed,
        capa_config=capa_config,
        rl_config=rl_config,
    )
    batch_agent = DDQNAgent(
        state_dim=4,
        action_dim=len(rl_config.batch_action_values()),
        learning_rate=training_config.learning_rate,
        discount_factor=training_config.discount_factor,
        epsilon_start=training_config.epsilon_start,
        epsilon_end=training_config.epsilon_end,
        epsilon_decay_steps=training_config.epsilon_decay_steps,
        target_update_interval=training_config.target_update_interval,
    )
    cross_agent = DDQNAgent(
        state_dim=4,
        action_dim=2,
        learning_rate=training_config.learning_rate,
        discount_factor=training_config.discount_factor,
        epsilon_start=training_config.epsilon_start,
        epsilon_end=training_config.epsilon_end,
        epsilon_decay_steps=training_config.epsilon_decay_steps,
        target_update_interval=training_config.target_update_interval,
    )
    batch_buffer = ReplayBuffer(training_config.replay_capacity)
    cross_buffer = ReplayBuffer(training_config.replay_capacity)

    episode_returns: list[float] = []
    batch_losses: list[float] = []
    cross_losses: list[float] = []

    for _episode_index in range(training_config.episodes):
        state_b = environment.reset()
        episode_return = 0.0
        episode_batch_losses: list[float] = []
        episode_cross_losses: list[float] = []

        while not environment.is_terminal():
            batch_action = batch_agent.select_action(state_b, explore=True)
            batch_duration = rl_config.batch_duration_from_action_index(batch_action)
            context = environment.start_batch(batch_duration=batch_duration)
            for transition in context.resolved_parcel_transitions:
                cross_buffer.push(transition)

            parcel_actions = {
                parcel_id: cross_agent.select_action(parcel_state, explore=True)
                for parcel_id, parcel_state in context.parcel_states.items()
            }
            step_result = environment.apply_parcel_actions(context, parcel_actions)

            batch_buffer.push(step_result.batch_transition)
            for transition in step_result.parcel_transitions:
                cross_buffer.push(transition)

            if len(batch_buffer) >= max(training_config.replay_warmup, training_config.batch_size):
                episode_batch_losses.append(batch_agent.train_step(batch_buffer, training_config.batch_size))
            if len(cross_buffer) >= max(training_config.replay_warmup, training_config.batch_size):
                episode_cross_losses.append(cross_agent.train_step(cross_buffer, training_config.batch_size))

            episode_return += step_result.batch_reward
            state_b = step_result.next_batch_state

        for transition in environment.finish_episode():
            cross_buffer.push(transition)
        if len(cross_buffer) >= max(training_config.replay_warmup, training_config.batch_size):
            episode_cross_losses.append(cross_agent.train_step(cross_buffer, training_config.batch_size))

        episode_returns.append(episode_return)
        batch_losses.append(float(np.mean(episode_batch_losses)) if episode_batch_losses else 0.0)
        cross_losses.append(float(np.mean(episode_cross_losses)) if episode_cross_losses else 0.0)

    batch_checkpoint = checkpoint_dir / "batch_agent.pt"
    cross_checkpoint = checkpoint_dir / "cross_agent.pt"
    batch_agent.save(batch_checkpoint)
    cross_agent.save(cross_checkpoint)

    summary = {
        "episode_returns": episode_returns,
        "loss_batch": batch_losses,
        "loss_cross": cross_losses,
        "epsilon_batch": batch_agent.current_epsilon(),
        "epsilon_cross": cross_agent.current_epsilon(),
        "checkpoint_dir": str(checkpoint_dir),
    }
    with (output_dir / "training_summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
    return summary


def _set_random_seed(seed: int) -> None:
    """Seed Python, NumPy, and PyTorch for reproducible RL-CAPA training.

    Args:
        seed: Random seed shared across libraries.
    """

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
