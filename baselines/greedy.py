"""Official Chengdu Greedy baseline entrypoint."""

from __future__ import annotations

import io
import re
from contextlib import redirect_stdout
from typing import Any


GREEDY_RESULT_PATTERN = re.compile(
    r"完成任务个数:\s*(?P<completed>[0-9.]+)\s*,\s*总失败个数:\s*(?P<failed>[0-9.]+)\s*,\s*任务完成率:\s*(?P<cr>[0-9.]+)\s*%.*?"
    r"批处理耗时:\s*(?P<bpt>[0-9.]+)\s*ms,\s*任务均报价:\s*(?P<avg_bid>[0-9.]+)\s*,\s*平台总报价:\s*(?P<platform_bid>[0-9.]+)\s*,\s*平台总收益:\s*(?P<tr>[0-9.]+)",
    re.DOTALL,
)


def safe_average(total: float, count: float) -> float:
    """Return a zero-safe average for legacy Greedy aggregate statistics."""
    if count == 0:
        return 0.0
    return total / count


def parse_greedy_metrics(output: str) -> dict[str, float]:
    """Parse the legacy Greedy stdout summary into normalized metric keys."""
    match = GREEDY_RESULT_PATTERN.search(output)
    if match is None:
        raise ValueError("Failed to parse Greedy output summary.")
    completed = int(float(match.group("completed")))
    return {
        "TR": float(match.group("tr")),
        "CR": float(match.group("cr")) / 100.0,
        "BPT": float(match.group("bpt")) / 1000.0,
        "delivered_parcels": completed,
        "accepted_assignments": completed,
    }


def run_greedy_baseline_environment(
    environment: Any,
    batch_size: int,
    utility: float = 0.5,
    realtime: int = 1,
) -> dict[str, float]:
    """Run the legacy Greedy baseline on a unified Chengdu environment and return normalized metrics."""
    import Framework_ChengDu as framework

    stdout_buffer = io.StringIO()
    with redirect_stdout(stdout_buffer):
        framework.Greedy(
            list(environment.station_set),
            list(environment.local_couriers),
            list(environment.tasks),
            batch_size,
            utility,
            realtime,
            getattr(environment, "service_radius_km", None),
        )
    return parse_greedy_metrics(stdout_buffer.getvalue())
