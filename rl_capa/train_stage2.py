"""Stage-2-only RL-CAPA ablation training entrypoint."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Mapping

from tqdm.auto import tqdm

from capa.models import CAPAConfig
from experiments.seeding import ChengduEnvironmentSeed
from rl_capa.config import RLCAPAConfig, RLTrainingConfig
from rl_capa.env import RLCAPAEnv
from rl_capa.stage2_trainer import Stage2RLCAPATrainer
from rl_capa.trainer import TrainingConfig
from rl_capa.visualize import plot_training_curves


def train_stage2_rl_capa(
    environment_seed: ChengduEnvironmentSeed,
    capa_config: CAPAConfig,
    rl_config: RLCAPAConfig,
    training_config: RLTrainingConfig,
    fixed_batch_size: int,
    output_dir: Path,
    progress_callback: Callable[[Mapping[str, float | int | bool]], None] | None = None,
) -> dict[str, Any]:
    """Train the fixed-batch stage-2-only RL-CAPA ablation."""

    output_dir.mkdir(parents=True, exist_ok=True)
    env = RLCAPAEnv(
        environment_seed=environment_seed,
        capa_config=capa_config,
        rl_config=rl_config,
    )
    trainer = Stage2RLCAPATrainer(
        env=env,
        config=TrainingConfig(
            num_episodes=training_config.episodes,
            discount_factor=training_config.discount_factor,
            lr_actor=training_config.lr_actor,
            lr_critic=training_config.lr_critic,
            entropy_coeff=training_config.entropy_coeff,
            max_grad_norm=training_config.max_grad_norm,
            max_steps_per_episode=training_config.max_steps_per_episode,
            normalize_advantages=training_config.normalize_advantages,
            device=training_config.device,
        ),
        fixed_batch_size=fixed_batch_size,
    )
    progress_bar = tqdm(
        total=training_config.episodes,
        desc="RL-CAPA stage2 train",
        unit="ep",
        disable=training_config.episodes <= 0,
    )

    def handle_progress(payload: Mapping[str, float | int | bool]) -> None:
        """Bridge trainer events to tqdm and optional external progress."""

        progress_bar.update(1)
        progress_bar.set_postfix(
            reward=f"{float(payload['total_reward']):.2f}",
            steps=int(payload["steps"]),
            cross=f"{float(payload['cross_rate']):.2f}",
            trunc="yes" if bool(payload["truncated"]) else "no",
        )
        if progress_callback is not None:
            progress_callback(payload)

    try:
        history = trainer.train(progress_callback=handle_progress)
    finally:
        progress_bar.close()
    training_plot_path = plot_training_curves(
        history=history,
        output_path=output_dir / "training_curves.png",
    )
    summary = {
        "variant": "rl-capa-stage2",
        "fixed_batch_size": fixed_batch_size,
        "episode_returns": [log.total_reward for log in history],
        "loss_pi1": [log.loss_pi1 for log in history],
        "loss_pi2": [log.loss_pi2 for log in history],
        "loss_v1": [log.loss_v1 for log in history],
        "loss_v2": [log.loss_v2 for log in history],
        "cross_rate": [log.cross_rate for log in history],
        "entropy_pi1": [log.entropy_pi1 for log in history],
        "entropy_pi2": [log.entropy_pi2 for log in history],
        "mean_batch_size": [log.mean_batch_size for log in history],
        "batch_size_sequences": [list(log.batch_sizes) for log in history],
        "batch_action_values": [int(fixed_batch_size)],
        "discount_factor": training_config.discount_factor,
        "device": str(trainer.device),
        "plots": {
            "training_curves": str(training_plot_path),
        },
    }
    with (output_dir / "training_summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
    return summary
