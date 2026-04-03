"""Evaluation entrypoint for trained RL-CAPA checkpoints."""

from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter
from typing import Any

from capa.metrics import compute_total_revenue
from capa.models import CAPAConfig
from experiments.seeding import ChengduEnvironmentSeed

from .config import RLCAPAConfig
from .ddqn import DDQNAgent
from .env import RLCAPAEnvironment


def evaluate_rl_capa(
    environment_seed: ChengduEnvironmentSeed,
    capa_config: CAPAConfig,
    rl_config: RLCAPAConfig,
    checkpoint_dir: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Evaluate one trained RL-CAPA policy without exploration.

    Args:
        environment_seed: Immutable Chengdu episode seed.
        capa_config: Shared CAPA configuration reused inside the environment.
        rl_config: RL-CAPA action-space configuration.
        checkpoint_dir: Directory containing the saved DDQN checkpoints.
        output_dir: Directory for the evaluation summary.

    Returns:
        Evaluation summary with paper-facing metrics.
    """

    batch_agent = DDQNAgent.load(checkpoint_dir / "batch_agent.pt")
    cross_agent = DDQNAgent.load(checkpoint_dir / "cross_agent.pt")
    environment = RLCAPAEnvironment(
        environment_seed=environment_seed,
        capa_config=capa_config,
        rl_config=rl_config,
    )
    state_b = environment.reset()
    decision_time_seconds = 0.0

    while not environment.is_terminal():
        started = perf_counter()
        batch_action = batch_agent.select_action(state_b, explore=False)
        decision_time_seconds += perf_counter() - started
        batch_duration = rl_config.batch_duration_from_action_index(batch_action)
        context = environment.start_batch(batch_duration=batch_duration)

        parcel_actions: dict[str, int] = {}
        for parcel_id, parcel_state in context.parcel_states.items():
            started = perf_counter()
            parcel_actions[parcel_id] = cross_agent.select_action(parcel_state, explore=False)
            decision_time_seconds += perf_counter() - started
        step_result = environment.apply_parcel_actions(context, parcel_actions)
        state_b = step_result.next_batch_state

    environment.finish_episode()
    environment.drain_routes()
    assignments = list(environment.accepted_assignments())
    metrics = {
        "TR": compute_total_revenue(assignments),
        "CR": (len(assignments) / environment.total_parcel_count()) if environment.total_parcel_count() > 0 else 0.0,
        "BPT": decision_time_seconds,
        "delivered_parcels": len(assignments),
        "accepted_assignments": len(assignments),
    }
    summary = {
        "algorithm": "rl-capa",
        "metrics": metrics,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
    return summary
