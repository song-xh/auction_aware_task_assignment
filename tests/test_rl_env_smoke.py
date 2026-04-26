"""Smoke tests for RL-CAPA's shared Chengdu environment adapter."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import torch

from capa.metrics import compute_batch_processing_time
from capa.models import CAPAConfig
from experiments.seeding import ChengduEnvironmentSeed
from rl_capa.config import RLCAPAConfig
from rl_capa.evaluate_core import evaluate
from rl_capa.env import RLCAPAEnv
from rl_capa.trainer import RLCAPATrainer, TrainingConfig


class DefaultTravelModel:
    """Small directed travel model that keeps every synthetic node reachable."""

    speed = 1.0

    def distance(self, start: object, end: object) -> float:
        """Return a deterministic positive distance between distinct nodes."""

        if start == end:
            return 0.0
        return 1.0

    def travel_time(self, start: object, end: object) -> float:
        """Return travel time equal to distance for tests."""

        return self.distance(start, end)


def _task(task_id: str, location: str, release: int = 0, deadline: int = 100, weight: float = 1.0) -> SimpleNamespace:
    """Build one legacy-like pickup task."""

    return SimpleNamespace(
        num=task_id,
        l_node=location,
        s_time=float(release),
        d_time=float(deadline),
        weight=float(weight),
        fare=10.0,
    )


def _courier(courier_id: int, location: str, station: SimpleNamespace, capacity: float = 10.0) -> SimpleNamespace:
    """Build one legacy-like courier."""

    return SimpleNamespace(
        num=courier_id,
        location=location,
        re_schedule=[],
        re_weight=0.0,
        max_weight=float(capacity),
        station=station,
        station_num=station.num,
        w=0.5,
        c=0.5,
        service_score=0.8,
        batch_take=0,
    )


def _seed(
    tasks: list[SimpleNamespace],
    local_capacity: float = 10.0,
    partner_count: int = 1,
) -> ChengduEnvironmentSeed:
    """Build one synthetic Chengdu seed for RL-CAPA tests."""

    station = SimpleNamespace(num=1, l_node="depot", f_pick_task_set=list(tasks), station_task_set=[])
    local_courier = _courier(1, "local", station, capacity=local_capacity)
    partner_couriers = [
        _courier(100 + index, f"partner-{index}", station, capacity=10.0)
        for index in range(partner_count)
    ]
    return ChengduEnvironmentSeed(
        tasks=tasks,
        local_couriers=[local_courier],
        partner_couriers_by_platform={"P1": partner_couriers} if partner_couriers else {},
        station_set=[station],
        travel_model=DefaultTravelModel(),
        platform_base_prices={"P1": 1.0} if partner_couriers else {},
        platform_sharing_rates={"P1": 0.5} if partner_couriers else {},
        platform_qualities={"P1": 1.0} if partner_couriers else {},
        movement_callback=_complete_routes,
    )


def _complete_routes(local_couriers: list[SimpleNamespace], partner_couriers: list[SimpleNamespace], *_args: object) -> None:
    """Simulate route progression by delivering all currently queued tasks."""

    for courier in [*local_couriers, *partner_couriers]:
        courier.re_schedule.clear()
        courier.re_weight = 0.0


def test_stage2_decisions_apply_to_full_batch_without_cama() -> None:
    """Stage 2 should decide local-vs-cross for every eligible batch parcel."""

    env = RLCAPAEnv(
        environment_seed=_seed([
            _task("local-task", "local-node"),
            _task("cross-task", "cross-node"),
        ]),
        capa_config=CAPAConfig(),
        rl_config=RLCAPAConfig(min_batch_size=10, max_batch_size=10),
    )

    env.reset()
    env.apply_batch_size(10)

    assert {parcel.parcel_id for parcel in env.current_eligible_parcels()} == {"local-task", "cross-task"}
    assert len(env.get_stage2_states()) == 2

    with patch("rl_capa.env.run_cama", create=True, side_effect=AssertionError("RL-CAPA should not call CAMA")):
        env.apply_stage2_decisions({"local-task": 0, "cross-task": 1})

    assignments = env.accepted_assignments()
    reports = env.batch_reports()
    assert [(assignment.parcel.parcel_id, assignment.mode) for assignment in assignments] == [
        ("local-task", "local"),
        ("cross-task", "cross"),
    ]
    assert len(reports[0].local_assignments) == 1
    assert len(reports[0].cross_assignments) == 1
    assert reports[0].unresolved_parcels == []


def test_local_stage_failure_returns_to_backlog_for_next_batch() -> None:
    """A parcel selected for local matching should retry later when local capacity fails."""

    env = RLCAPAEnv(
        environment_seed=_seed([
            _task("heavy", "heavy-node", weight=5.0),
            _task("future", "future-node", release=100),
        ], local_capacity=1.0, partner_count=0),
        capa_config=CAPAConfig(),
        rl_config=RLCAPAConfig(min_batch_size=10, max_batch_size=10),
    )

    env.reset()
    env.apply_batch_size(10)
    env.apply_stage2_decisions({"heavy": 0})

    assert [parcel.parcel_id for parcel in env.batch_reports()[0].unresolved_parcels] == ["heavy"]
    assert not env.is_done()


def test_stage1_state_uses_six_dimensions_and_true_future_window() -> None:
    """Stage 1 should expose true future parcel/courier counts in a 6D state."""

    seed = _seed([
        _task("now", "now-node", release=0),
        _task("soon", "soon-node", release=5),
        _task("later", "later-node", release=50),
    ])
    short_env = RLCAPAEnv(
        environment_seed=seed,
        capa_config=CAPAConfig(),
        rl_config=RLCAPAConfig(min_batch_size=10, max_batch_size=10, future_feature_window_seconds=10),
    )
    long_env = RLCAPAEnv(
        environment_seed=seed,
        capa_config=CAPAConfig(),
        rl_config=RLCAPAConfig(min_batch_size=10, max_batch_size=10, future_feature_window_seconds=100),
    )

    short_env.reset()
    long_env.reset()
    short_state = short_env.get_stage1_state()
    long_state = long_env.get_stage1_state()

    assert short_state.shape == (6,)
    assert long_state.shape == (6,)
    assert short_state[2] == 1.0
    assert long_state[2] == 2.0


def test_trainer_uses_six_dimensional_stage1_networks_and_adam() -> None:
    """Trainer dimensions should match 6D stage-1 state while keeping Adam."""

    env = RLCAPAEnv(
        environment_seed=_seed([_task("now", "now-node")]),
        capa_config=CAPAConfig(),
        rl_config=RLCAPAConfig(min_batch_size=10, max_batch_size=10),
    )
    trainer = RLCAPATrainer(env=env, config=TrainingConfig(num_episodes=0), num_batch_actions=1)

    assert trainer.norm_s1.dim == 6
    assert trainer.pi1.net[0].in_features == 6
    assert trainer.v1.net[0].in_features == 6
    assert isinstance(trainer.opt_pi1, torch.optim.Adam)


def test_evaluate_bpt_matches_environment_batch_reports() -> None:
    """RL-CAPA evaluation BPT should aggregate unified environment batch timing."""

    env = RLCAPAEnv(
        environment_seed=_seed([_task("now", "now-node")]),
        capa_config=CAPAConfig(),
        rl_config=RLCAPAConfig(min_batch_size=10, max_batch_size=10),
    )
    trainer = RLCAPATrainer(env=env, config=TrainingConfig(num_episodes=0), num_batch_actions=1)

    result = evaluate(env=env, trainer=trainer, batch_action_values=[10], max_steps=5)

    assert result.batch_processing_time == compute_batch_processing_time(env.batch_reports())
