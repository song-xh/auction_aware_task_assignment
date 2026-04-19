"""RL-CAPA evaluation mode (spec Section 12).

Greedy evaluation:
  - pi1: argmax (most probable batch size)
  - pi2: threshold 0.5 (P(a=1) > 0.5 -> cross)
  - No gradient updates
  - Reports TR, CR, BPT aligned with CAPA metrics
"""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import List

import numpy as np
import torch

from rl_capa.state_builder import RunningNormalizer, aggregate_stage2_states


@dataclass
class EvalResult:
    """Evaluation metrics aligned with CAPA paper.

    Args:
        total_revenue: TR -- sum of local_platform_revenue over all assignments.
        completion_rate: CR -- fraction of parcels assigned.
        batch_processing_time: BPT -- total wall-clock decision time in seconds.
        total_parcels: Total parcels in the episode.
        assignments: Number of accepted assignments.
        steps: Number of environment steps.
    """

    total_revenue: float
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
) -> EvalResult:
    """Run one greedy evaluation episode.

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
    total_decision_time = 0.0

    with torch.no_grad():
        while not env.is_done() and step < max_steps:
            step += 1

            # Stage 1: argmax batch size
            t_start = perf_counter()
            s1_raw = env.get_stage1_state()
            s1_norm = norm_s1.normalize(s1_raw)
            s1_tensor = torch.from_numpy(s1_norm).to(device)
            dist1 = pi1(s1_tensor)
            a1_index = dist1.probs.argmax().item()
            batch_duration = batch_action_values[a1_index]
            total_decision_time += perf_counter() - t_start

            env.apply_batch_size(batch_duration)
            local_assignments, unassigned = env.run_local_matching()

            # Stage 2: threshold 0.5
            t_stage2 = perf_counter()
            s2_list = env.get_stage2_states(unassigned)
            if s2_list:
                s2_normed = [norm_s2.normalize(s) for s in s2_list]
                s2_tensor = torch.from_numpy(np.stack(s2_normed)).to(device)
                dist2 = pi2(s2_tensor)
                probs = dist2.probs
                actions = (probs > 0.5).long()
                decisions = {
                    p.parcel_id: int(a.item())
                    for p, a in zip(unassigned, actions)
                }
            else:
                decisions = {}
            total_decision_time += perf_counter() - t_stage2

            env.apply_cross_decisions(decisions)

    env.finalize_episode()

    accepted = env.accepted_assignments()
    delivered_parcels = env.delivered_parcels()
    total_revenue = sum(a.local_platform_revenue for a in accepted)
    completion_rate = len(delivered_parcels) / max(total_parcels, 1)

    pi1.train()
    pi2.train()

    return EvalResult(
        total_revenue=total_revenue,
        completion_rate=completion_rate,
        batch_processing_time=total_decision_time,
        total_parcels=total_parcels,
        assignments=len(accepted),
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

    from capa.metrics import compute_total_revenue
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
        completion_rate=result.metrics.completion_rate,
        batch_processing_time=result.metrics.batch_processing_time,
        total_parcels=len(environment.tasks),
        assignments=result.metrics.delivered_parcel_count,
        steps=len(result.batch_reports),
    )
