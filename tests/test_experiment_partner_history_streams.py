"""Tests for cooperating-platform own-task stream construction and seeding."""

from __future__ import annotations

from types import SimpleNamespace

from env.chengdu import ChengduEnvironment, build_partner_own_task_streams
from experiments.seeding import build_environment_seed, derive_environment_from_seed


def _station() -> SimpleNamespace:
    """Build one synthetic station covering all test tasks."""

    return SimpleNamespace(station_range=(104.0, 105.0, 30.0, 31.0), f_pick_task_set=[])


def _task(task_id: str, request_time: int) -> SimpleNamespace:
    """Build one minimal synthetic legacy pick task."""

    return SimpleNamespace(
        num=task_id,
        s_time=str(request_time),
        d_time=str(request_time + 300),
        l_lng="104.5",
        l_lat="30.5",
        fare=10.0,
    )


def test_build_partner_own_task_streams_uses_platform_specific_counts() -> None:
    """Each partner platform should receive its own deterministic stream size."""

    station = _station()
    ordered_tasks = [_task(f"p{index}", index * 10) for index in range(20)]

    streams = build_partner_own_task_streams(
        station_set=[station],
        ordered_pick_tasks=ordered_tasks,
        platform_task_counts={"P1": 4, "P2": 6},
        window_start_seconds=None,
        window_end_seconds=None,
        sampling_seed=7,
        excluded_task_ids={"p0", "p1"},
    )

    assert len(streams["P1"]) == 4
    assert len(streams["P2"]) == 6
    assert {"p0", "p1"}.isdisjoint({task.num for task in streams["P1"]})
    assert {"p0", "p1"}.isdisjoint({task.num for task in streams["P2"]})
    assert [float(task.s_time) for task in streams["P1"]] == sorted(float(task.s_time) for task in streams["P1"])
    assert [float(task.s_time) for task in streams["P2"]] == sorted(float(task.s_time) for task in streams["P2"])


def test_build_partner_own_task_streams_keeps_platform_seed_stable_under_prefix_filter() -> None:
    """One platform's stream should not change when later platforms are added."""

    station = _station()
    ordered_tasks = [_task(f"p{index}", index * 10) for index in range(25)]
    platform_task_counts = {"P1": 5, "P2": 7}

    prefix_only = build_partner_own_task_streams(
        station_set=[station],
        ordered_pick_tasks=ordered_tasks,
        platform_task_counts={"P1": platform_task_counts["P1"]},
        sampling_seed=11,
    )
    with_suffix = build_partner_own_task_streams(
        station_set=[station],
        ordered_pick_tasks=ordered_tasks,
        platform_task_counts=platform_task_counts,
        sampling_seed=11,
    )

    assert [task.num for task in prefix_only["P1"]] == [task.num for task in with_suffix["P1"]]


def test_derive_environment_from_seed_keeps_partner_own_task_streams_full_length() -> None:
    """Reducing local parcel count should not truncate partner own-task streams."""

    environment = ChengduEnvironment(
        tasks=[_task(f"local-{index}", index * 10) for index in range(8)],
        local_couriers=[],
        partner_couriers_by_platform={"P1": [], "P2": []},
        station_set=[_station()],
        travel_model=SimpleNamespace(),
        platform_base_prices={"P1": 1.0, "P2": 1.5},
        platform_sharing_rates={"P1": 0.5, "P2": 0.6},
        platform_qualities={"P1": 1.0, "P2": 0.9},
        partner_tasks_by_platform={
            "P1": [_task(f"partner-1-{index}", index * 5) for index in range(12)],
            "P2": [_task(f"partner-2-{index}", index * 6) for index in range(15)],
        },
    )

    seed = build_environment_seed(environment)
    derived = derive_environment_from_seed(seed, num_parcels=3)

    assert len(derived.tasks) == 3
    assert len(derived.partner_tasks_by_platform["P1"]) == 12
    assert len(derived.partner_tasks_by_platform["P2"]) == 15
