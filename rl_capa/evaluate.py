"""Actor-critic RL-CAPA evaluation entrypoint."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from algorithms.summary_utils import build_decision_trace
from capa.models import CAPAConfig
from experiments.seeding import ChengduEnvironmentSeed

from .config import RLCAPAConfig, RLTrainingConfig
from .env import RLCAPAEnv
from .evaluate_core import EvalResult, evaluate, run_capa_baseline
from .trainer import RLCAPATrainer, TrainingConfig
from .visualize import plot_evaluation_curves


def evaluate_rl_capa(
    environment_seed: ChengduEnvironmentSeed,
    capa_config: CAPAConfig,
    rl_config: RLCAPAConfig,
    checkpoint_dir: Path,
    output_dir: Path,
    training_config: RLTrainingConfig | None = None,
    eval_stochastic: bool = True,
    eval_seeds: int = 5,
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
            normalize_advantages=restored_training.normalize_advantages,
            device=restored_training.device,
        ),
        num_batch_actions=len(rl_config.batch_action_values()),
        checkpoint_dir=checkpoint_dir,
    )
    import torch

    seed_count = max(1, int(eval_seeds))
    per_seed_results: list[Any] = []
    for seed_index in range(seed_count):
        torch.manual_seed(seed_index)
        per_seed_results.append(
            evaluate(
                env=env,
                trainer=trainer,
                batch_action_values=rl_config.batch_action_values(),
                eval_stochastic=eval_stochastic,
            )
        )
    # Use the final per-seed env state for decision_trace, but report
    # averaged metrics so stochastic-policy variance does not dominate
    # the reported TR.
    result = per_seed_results[-1]
    averaged_total_revenue = sum(r.total_revenue for r in per_seed_results) / len(per_seed_results)
    averaged_completion_rate = sum(r.completion_rate for r in per_seed_results) / len(per_seed_results)
    averaged_bpt = sum(r.batch_processing_time for r in per_seed_results) / len(per_seed_results)
    delivered_assignments = list(env.delivered_assignments())
    delivered_ids = {
        str(getattr(assignment.parcel, "parcel_id", ""))
        for assignment in delivered_assignments
    }
    timed_out_assignments_objects = [
        assignment for assignment in env.accepted_assignments()
        if str(getattr(assignment.parcel, "parcel_id", "")) not in delivered_ids
    ]
    accepted_ids = {
        str(getattr(assignment.parcel, "parcel_id", ""))
        for assignment in env.accepted_assignments()
    }
    unmatched_ids = [
        str(getattr(task, "num"))
        for task in env.terminal_unassigned_tasks()
        if str(getattr(task, "num")) not in accepted_ids
    ]
    summary = {
        "algorithm": "rl-capa",
        "variant": "rl-capa-svc" if rl_config.use_service_slack else "rl-capa",
        "use_service_slack": rl_config.use_service_slack,
        "metrics": {
            "TR": averaged_total_revenue,
            "CR": averaged_completion_rate,
            "BPT": averaged_bpt,
            "delivered_parcels": len(env.delivered_parcels()),
            "accepted_assignments": len(env.accepted_assignments()),
            "timed_out_parcels": len(env.timed_out_parcels()),
            **env.disposition_breakdown(),
            "eval_stochastic": bool(eval_stochastic),
            "eval_seeds": seed_count,
            "eval_per_seed_TR": [r.total_revenue for r in per_seed_results],
        },
        "decision_trace": build_decision_trace(
            delivered_assignments=delivered_assignments,
            timed_out_assignments=timed_out_assignments_objects,
            unassigned_parcel_ids=unmatched_ids,
        ),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    summary["plots"] = plot_evaluation_curves(
        batch_reports=env.batch_reports(),
        total_parcels=result.total_parcels,
        total_revenue=result.total_revenue,
        completion_rate=result.completion_rate,
        batch_processing_time=result.batch_processing_time,
        output_dir=output_dir,
    )
    with (output_dir / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
    return summary


__all__ = [
    "EvalResult",
    "evaluate",
    "run_capa_baseline",
    "evaluate_rl_capa",
]
