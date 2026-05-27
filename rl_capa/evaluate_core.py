"""RL-CAPA evaluation mode (spec Section 12).

Greedy evaluation:
  - pi1: argmax (most probable batch size)
  - pi2: threshold 0.5 (P(a=1) > 0.5 -> cross)
  - No gradient updates
  - Reports TR, CR, BPT aligned with CAPA metrics
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np
import torch

from capa.metrics import compute_batch_processing_time, compute_cross_revenue, compute_local_revenue
from rl_capa.state_builder import RunningNormalizer, aggregate_stage2_states


@dataclass
class EvalResult:
    """Evaluation metrics aligned with CAPA paper.

    Args:
        total_revenue: TR -- sum of local_platform_revenue over all assignments.
        local_revenue: Portion of TR realized from local assignments.
        cross_revenue: Portion of TR realized from cross assignments.
        completion_rate: CR -- fraction of parcels assigned.
        batch_processing_time: BPT -- total wall-clock decision time in seconds.
        total_parcels: Total parcels in the episode.
        assignments: Number of accepted assignments.
        steps: Number of environment steps.
    """

    total_revenue: float
    local_revenue: float
    cross_revenue: float
    completion_rate: float
    batch_processing_time: float
    total_parcels: int
    assignments: int
    steps: int


def evaluate(
    env: object,
    trainer: object,
    batch_action_values: List[int],
    max_steps: int = 500,
    eval_stochastic: bool = True,
) -> EvalResult:
    """Run one evaluation episode.

    Args:
        env: RLCAPAEnv instance.
        trainer: RLCAPATrainer with trained networks.
        batch_action_values: Ordered batch duration values for A_b.
        max_steps: Safety step limit.

    Returns:
        EvalResult with TR, CR, BPT.
    """
    pi1 = trainer.pi1
    pi2 = trainer.pi2
    norm_s1 = trainer.norm_s1
    norm_s2 = trainer.norm_s2
    device = trainer.device

    pi1.eval()
    pi2.eval()

    info = env.reset()
    total_parcels = info["total_parcels"]
    step = 0
    # Match the trainer's stochastic action sampling so reported eval TR is
    # consistent with the per-episode reward during training. The previous
    # deterministic eval (pi1.argmax + pi2 threshold 0.5) silently diverged
    # from training reward whenever pi2 had not converged to a bimodal
    # policy: a marginal p=0.55 pushes every parcel to cross at threshold
    # but only 55% during stochastic training, producing a multi-hundred-TR
    # gap on the same checkpoint. The greedy variant remains accessible
    # via ``eval_stochastic = False`` for sanity checks.

    with torch.no_grad():
        while not env.is_done() and step < max_steps:
            step += 1

            s1_raw = env.get_stage1_state()
            s1_norm = norm_s1.normalize(s1_raw)
            s1_tensor = torch.from_numpy(s1_norm).to(device)
            dist1 = pi1(s1_tensor)
            if eval_stochastic:
                a1_index = int(dist1.sample().item())
            else:
                a1_index = int(dist1.probs.argmax().item())
            batch_duration = batch_action_values[a1_index]

            env.apply_batch_size(batch_duration)
            batch_parcels = env.current_eligible_parcels()

            s2_list = env.get_stage2_states(batch_parcels)
            if s2_list:
                s2_normed = [norm_s2.normalize(s) for s in s2_list]
                s2_tensor = torch.from_numpy(np.stack(s2_normed)).to(device)
                dist2 = pi2(s2_tensor)
                if eval_stochastic:
                    actions = dist2.sample().long()
                else:
                    actions = (dist2.probs > 0.5).long()
                decisions = {
                    p.parcel_id: int(a.item())
                    for p, a in zip(batch_parcels, actions)
                }
            else:
                decisions = {}

            env.apply_stage2_decisions(decisions)

    env.finalize_episode()

    accepted = env.accepted_assignments()
    delivered_assignments = env.delivered_assignments()
    delivered_parcels = env.delivered_parcels()
    total_revenue = sum(a.local_platform_revenue for a in delivered_assignments)
    completion_rate = len(delivered_parcels) / max(total_parcels, 1)

    pi1.train()
    pi2.train()

    return EvalResult(
        total_revenue=total_revenue,
        local_revenue=compute_local_revenue(delivered_assignments),
        cross_revenue=compute_cross_revenue(delivered_assignments),
        completion_rate=completion_rate,
        batch_processing_time=compute_batch_processing_time(env.batch_reports()),
        total_parcels=total_parcels,
        assignments=len(delivered_assignments),
        steps=step,
    )


def run_capa_baseline(
    seed: object,
    capa_config: object,
    batch_seconds: int = 15,
) -> EvalResult:
    """Run fixed-policy CAPA baseline for comparison.

    Args:
        seed: ChengduEnvironmentSeed.
        capa_config: CAPAConfig.
        batch_seconds: Fixed batch size for CAPA.

    Returns:
        EvalResult with CAPA's TR, CR, BPT.
    """
    from time import perf_counter

    from experiments.seeding import clone_environment_from_seed
    from env.chengdu import (
        run_time_stepped_chengdu_batches,
        framework_movement_callback,
    )

    environment = clone_environment_from_seed(seed)
    t_start = perf_counter()
    result = run_time_stepped_chengdu_batches(
        tasks=environment.tasks,
        local_couriers=environment.local_couriers,
        partner_couriers_by_platform=environment.partner_couriers_by_platform,
        station_set=environment.station_set,
        travel_model=environment.travel_model,
        config=capa_config,
        batch_seconds=batch_seconds,
        step_seconds=60,
        platform_base_prices=environment.platform_base_prices,
        platform_sharing_rates=environment.platform_sharing_rates,
        platform_qualities=environment.platform_qualities,
        movement_callback=environment.movement_callback or framework_movement_callback,
        service_radius_km=environment.service_radius_km,
    )
    _ = perf_counter() - t_start

    return EvalResult(
        total_revenue=result.metrics.total_revenue,
        local_revenue=result.metrics.local_revenue,
        cross_revenue=result.metrics.cross_revenue,
        completion_rate=result.metrics.completion_rate,
        batch_processing_time=result.metrics.batch_processing_time,
        total_parcels=len(environment.tasks),
        assignments=result.metrics.delivered_parcel_count,
        steps=len(result.batch_reports),
    )
