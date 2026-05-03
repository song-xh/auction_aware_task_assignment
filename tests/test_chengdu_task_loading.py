"""Tests for Chengdu task ingestion from split order files."""

from __future__ import annotations

from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from Tasks_ChengDu import readTask
from env.chengdu import select_station_pick_tasks


def _task_line(task_id: str, fare: float) -> str:
    """Build one legacy Chengdu task CSV row for loader tests."""

    return f"{task_id},30.0,104.0,node-{task_id},1,10,1.0,{fare}\n"


def test_read_task_loads_every_row_from_third_order_split() -> None:
    """Ensure the third split is parsed row-by-row, not only by its final row."""

    files = {
        "Data/order_20161101_deal1": _task_line("p1", 8.0),
        "Data/order_20161101_deal2": _task_line("p2", 8.0),
        "Data/order_20161101_deal3": "".join(
            [
                _task_line("p3a", 8.0),
                _task_line("p3b", 8.0),
                _task_line("d3", 0.0),
            ]
        ),
        "Data/order_20161101_deal4": _task_line("p4", 8.0),
        "Data/order_20161101_deal5": _task_line("p5", 8.0),
        "Data/order_20161101_deal6": _task_line("p6", 8.0),
        "Data/order_20161101_deal7": _task_line("p7", 8.0),
        "Data/order_20161101_deal8": _task_line("p8", 8.0),
    }

    def fake_open(path: str, *args: object, **kwargs: object) -> StringIO:
        """Return per-file task content for the hard-coded loader paths."""

        del args, kwargs
        return StringIO(files[path])

    with patch("builtins.open", side_effect=fake_open):
        pick_tasks, delivery_tasks = readTask()

    pick_ids = {task.num for task in pick_tasks}
    delivery_ids = {task.num for task in delivery_tasks}

    assert {"p1", "p2", "p3a", "p3b", "p4", "p5", "p6", "p7", "p8"} <= pick_ids
    assert "d3" in delivery_ids


def test_generated_chengdu_splits_are_pickup_majority() -> None:
    """Generated supplemental splits should contain more pick-up than delivery tasks."""

    for split_index in range(5, 9):
        rows = [
            line.split(",")
            for line in Path(f"Data/order_20161101_deal{split_index}")
            .read_text(encoding="utf-8")
            .replace("\r", "\n")
            .strip()
            .splitlines()
        ]
        pick_count = sum(float(row[7]) != 0.0 for row in rows)
        delivery_count = len(rows) - pick_count

        assert pick_count > delivery_count
        assert pick_count / len(rows) >= 0.8


def _legacy_pick_task(task_id: str, request_time: int) -> SimpleNamespace:
    """Build one minimal station-bounded legacy pick task."""

    return SimpleNamespace(
        num=task_id,
        s_time=str(request_time),
        d_time=str(request_time + 100),
        l_lng="104.5",
        l_lat="30.5",
    )


def _station() -> SimpleNamespace:
    """Build one minimal station covering all synthetic test tasks."""

    return SimpleNamespace(station_range=(104.0, 105.0, 30.0, 31.0), f_pick_task_set=[])


def test_select_station_pick_tasks_defaults_to_full_dataset_time_window() -> None:
    """Default sampling bounds should use the min/max task request times."""

    station = _station()
    tasks = [_legacy_pick_task(f"p{index}", index * 10) for index in range(6)]

    selected = select_station_pick_tasks(
        station_set=[station],
        ordered_pick_tasks=tasks,
        num_parcels=6,
        sampling_seed=99,
    )

    assert [task.num for task in selected] == [task.num for task in tasks]
    assert station.f_pick_task_set == selected


def test_select_station_pick_tasks_samples_deterministically_then_sorts_by_time() -> None:
    """Sampling should be seed-stable and playback should remain chronological."""

    station_a = _station()
    station_b = _station()
    station_c = _station()
    tasks = [_legacy_pick_task(f"p{index}", index * 10) for index in range(12)]

    selected_a = select_station_pick_tasks(
        station_set=[station_a],
        ordered_pick_tasks=tasks,
        num_parcels=5,
        sampling_seed=7,
    )
    selected_b = select_station_pick_tasks(
        station_set=[station_b],
        ordered_pick_tasks=tasks,
        num_parcels=5,
        sampling_seed=7,
    )
    selected_c = select_station_pick_tasks(
        station_set=[station_c],
        ordered_pick_tasks=tasks,
        num_parcels=5,
        sampling_seed=8,
    )

    assert [task.num for task in selected_a] == [task.num for task in selected_b]
    assert [task.num for task in selected_a] != [task.num for task in selected_c]
    assert [float(task.s_time) for task in selected_a] == sorted(float(task.s_time) for task in selected_a)


def test_select_station_pick_tasks_respects_explicit_time_window() -> None:
    """Explicit time-window bounds should filter candidates before sampling."""

    station = _station()
    tasks = [_legacy_pick_task(f"p{index}", index * 10) for index in range(10)]

    selected = select_station_pick_tasks(
        station_set=[station],
        ordered_pick_tasks=tasks,
        num_parcels=3,
        window_start_seconds=20,
        window_end_seconds=40,
        sampling_seed=1,
    )

    assert [task.num for task in selected] == ["p2", "p3", "p4"]
