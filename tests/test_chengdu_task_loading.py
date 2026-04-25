"""Tests for Chengdu task ingestion from split order files."""

from __future__ import annotations

from io import StringIO
from unittest.mock import patch

from Tasks_ChengDu import readTask


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
    }

    def fake_open(path: str, *args: object, **kwargs: object) -> StringIO:
        """Return per-file task content for the hard-coded loader paths."""

        del args, kwargs
        return StringIO(files[path])

    with patch("builtins.open", side_effect=fake_open):
        pick_tasks, delivery_tasks = readTask()

    pick_ids = {task.num for task in pick_tasks}
    delivery_ids = {task.num for task in delivery_tasks}

    assert {"p1", "p2", "p3a", "p3b", "p4"} <= pick_ids
    assert "d3" in delivery_ids
