"""Actor-critic RL-CAPA evaluation entrypoint."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from capa.models import CAPAConfig
from experiments.seeding import ChengduEnvironmentSeed

from .config import RLCAPAConfig, RLTrainingConfig
from .env import RLCAPAEnv
from .evaluate_core import EvalResult, evaluate, run_capa_baseline
from .trainer import RLCAPATrainer, TrainingConfig


def evaluate_rl_capa(
    environment_seed: ChengduEnvironmentSeed,
    capa_config: CAPAConfig,
    rl_config: RLCAPAConfig,
    checkpoint_dir: Path,
    output_dir: Path,
    training_config: RLTrainingConfig | None = None,
) -> dict[str, Any]:
    """Evaluate one trained actor-critic RL-CAPA checkpoint set.

    Args:
        environment_seed: Immutable Chengdu environment seed.
        capa_config: Shared CAPA configuration.
        rl_config: RL environment configuration.
        checkpoint_dir: Directory containing actor-critic checkpoints.
        output_dir: Directory for the evaluation summary.
        training_config: Optional training hyperparameters used to rebuild the trainer.

    Returns:
        JSON-serializable evaluation summary.
    """

    restored_training = training_config or RLTrainingConfig()
    env = RLCAPAEnv(
        environment_seed=environment_seed,
        capa_config=capa_config,
        rl_config=rl_config,
    )
    trainer = RLCAPATrainer.load_checkpoint(
        env=env,
        config=TrainingConfig(
            num_episodes=restored_training.episodes,
            discount_factor=restored_training.discount_factor,
            lr_actor=restored_training.lr_actor,
            lr_critic=restored_training.lr_critic,
            entropy_coeff=restored_training.entropy_coeff,
            max_grad_norm=restored_training.max_grad_norm,
            max_steps_per_episode=restored_training.max_steps_per_episode,
            device=restored_training.device,
        ),
        num_batch_actions=len(rl_config.batch_action_values()),
        checkpoint_dir=checkpoint_dir,
    )
    result = evaluate(
        env=env,
        trainer=trainer,
        batch_action_values=rl_config.batch_action_values(),
    )
    summary = {
        "algorithm": "rl-capa",
        "metrics": {
            "TR": result.total_revenue,
            "CR": result.completion_rate,
            "BPT": result.batch_processing_time,
            "delivered_parcels": len(env.delivered_parcels()),
            "accepted_assignments": len(env.accepted_assignments()),
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
    return summary


__all__ = [
    "EvalResult",
    "evaluate",
    "run_capa_baseline",
    "evaluate_rl_capa",
]
