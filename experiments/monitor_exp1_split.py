"""External monitoring helpers for split-process Exp-1 runs."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any


def collect_split_progress(tmp_root: Path) -> dict[str, Any]:
    """Collect one normalized progress snapshot from a split Exp-1 temp root.

    Args:
        tmp_root: Temporary root used by `run_exp1_split.py`.

    Returns:
        One progress dictionary summarizing point and algorithm completion.
    """

    status_path = tmp_root / "split_status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    points: dict[str, Any] = {}
    completed_points = 0
    for point_value, point_status in status.get("points", {}).items():
        output_dir = Path(point_status["output_dir"])
        completed_algorithms = sorted(
            child.name
            for child in output_dir.iterdir()
            if child.is_dir() and (child / "summary.json").exists()
        ) if output_dir.exists() else []
        point_complete = (output_dir / "summary.json").exists()
        if point_complete:
            completed_points += 1
        points[str(point_value)] = {
            "pid": point_status.get("pid"),
            "returncode": point_status.get("returncode"),
            "output_dir": str(output_dir),
            "completed_algorithms": completed_algorithms,
            "point_complete": point_complete,
        }
    return {
        "state": status.get("state", "unknown"),
        "updated_at": status.get("updated_at"),
        "tmp_root": str(tmp_root),
        "total_points": len(points),
        "completed_points": completed_points,
        "points": points,
    }


def monitor_split_progress(
    tmp_root: Path,
    snapshot_path: Path,
    log_path: Path,
    poll_seconds: int = 30,
    max_iterations: int | None = None,
) -> dict[str, Any]:
    """Monitor one split Exp-1 run and write rolling snapshots plus append-only logs.

    Args:
        tmp_root: Temporary root used by `run_exp1_split.py`.
        snapshot_path: JSON snapshot output path.
        log_path: Append-only text log path.
        poll_seconds: Sleep interval between polls.
        max_iterations: Optional upper bound for loop iterations.

    Returns:
        The last collected progress snapshot.
    """

    iteration = 0
    last_snapshot: dict[str, Any] | None = None
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    while True:
        iteration += 1
        snapshot = collect_split_progress(tmp_root)
        snapshot_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
        _append_log_line(log_path=log_path, snapshot=snapshot)
        last_snapshot = snapshot
        if snapshot["state"] == "finished":
            break
        if max_iterations is not None and iteration >= max_iterations:
            break
        time.sleep(poll_seconds)
    return last_snapshot or {}


def _append_log_line(log_path: Path, snapshot: dict[str, Any]) -> None:
    """Append one human-readable progress line for operators watching a live run.

    Args:
        log_path: Append-only log path.
        snapshot: Progress snapshot to serialize.
    """

    point_parts = []
    for point_value in sorted(snapshot["points"], key=lambda value: int(value)):
        point = snapshot["points"][point_value]
        algorithms = ",".join(point["completed_algorithms"]) or "-"
        suffix = "done" if point["point_complete"] else "running"
        point_parts.append(f"{point_value}:algos={algorithms}:state={suffix}")
    line = (
        f"{datetime.now().isoformat(timespec='seconds')} "
        f"state={snapshot['state']} "
        f"completed_points={snapshot['completed_points']}/{snapshot['total_points']} "
        f"{' | '.join(point_parts)}"
    )
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"{line}\n")


def main() -> int:
    """Parse CLI arguments and start monitoring one split Exp-1 run."""

    parser = argparse.ArgumentParser(description="Monitor a split-process Exp-1 run from /tmp.")
    parser.add_argument("--tmp-root", required=True)
    parser.add_argument("--snapshot-path", required=True)
    parser.add_argument("--log-path", required=True)
    parser.add_argument("--poll-seconds", type=int, default=30)
    parser.add_argument("--max-iterations", type=int, default=None)
    args = parser.parse_args()
    monitor_split_progress(
        tmp_root=Path(args.tmp_root),
        snapshot_path=Path(args.snapshot_path),
        log_path=Path(args.log_path),
        poll_seconds=args.poll_seconds,
        max_iterations=args.max_iterations,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
