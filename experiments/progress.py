"""Shared progress rendering helpers for long-running Chengdu experiment scripts."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Literal, Mapping


ProgressMode = Literal["overwrite", "append", "auto"]


def render_progress_bar(completed: float, total: float, width: int = 36) -> str:
    """Render one bounded ASCII progress bar.

    Args:
        completed: Completed work units.
        total: Total work units.
        width: Number of fill characters inside the bar.

    Returns:
        One formatted bar string with percentage text.
    """

    normalized_total = max(float(total), 1.0)
    ratio = min(max(float(completed) / normalized_total, 0.0), 1.0)
    filled = min(width, max(0, int(round(ratio * width))))
    empty = max(0, width - filled)
    return f"[{'#' * filled}{'-' * empty}] {ratio * 100.0:4.1f}%"


def write_point_progress(progress_path: Path, snapshot: Mapping[str, Any]) -> None:
    """Persist one point-level progress snapshot as JSON.

    Args:
        progress_path: Output path for the progress snapshot.
        snapshot: Snapshot payload to serialize.
    """

    progress_path.parent.mkdir(parents=True, exist_ok=True)
    progress_path.write_text(json.dumps(dict(snapshot), indent=2), encoding="utf-8")


def read_point_progress(progress_path: Path) -> dict[str, Any] | None:
    """Load one point-level progress snapshot when present.

    Args:
        progress_path: Path to one point progress file.

    Returns:
        The parsed snapshot, or `None` if the file does not exist.
    """

    if not progress_path.exists():
        return None
    return json.loads(progress_path.read_text(encoding="utf-8"))


def compute_point_algorithm_units(point_snapshot: Mapping[str, Any]) -> float:
    """Compute completed algorithm units for one point, including active fractional progress.

    Args:
        point_snapshot: One point entry inside a collected split snapshot.

    Returns:
        The completed algorithm count plus fractional progress for the active algorithm.
    """

    completed = float(len(point_snapshot.get("completed_algorithms", [])))
    last_event = point_snapshot.get("last_event") or {}
    phase = str(last_event.get("phase", ""))
    completed_units = float(last_event.get("completed_units", 0.0) or 0.0)
    total_units = float(last_event.get("total_units", 0.0) or 0.0)
    batch_index = int(last_event.get("batch_index", 1) or 1)
    total_batches = int(last_event.get("total_batches", 1) or 1)
    effective_batches = max(total_batches, batch_index, 1)
    if total_units <= 0.0:
        fractional = 0.0
    else:
        unit_fraction = min(max(completed_units / total_units, 0.0), 1.0)
        if phase == "batch_completed":
            fractional = batch_index / effective_batches
        elif phase == "cama_parcel_progress":
            fractional = ((batch_index - 1) + (0.5 * unit_fraction)) / effective_batches
        elif phase == "dapa_parcel_progress":
            fractional = ((batch_index - 1) + 0.5 + (0.5 * unit_fraction)) / effective_batches
        elif phase == "batch_matching":
            fractional = (batch_index - 1) / effective_batches
        else:
            fractional = min(unit_fraction, 0.05)
    if point_snapshot.get("point_complete"):
        fractional = 0.0
    return completed + fractional


def enrich_split_snapshot(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Augment one split snapshot with aggregate algorithm-unit progress.

    Args:
        snapshot: Raw split snapshot.

    Returns:
        A copy enriched with `completed_algorithm_units` and `total_algorithm_units`.
    """

    enriched = dict(snapshot)
    points = {str(key): dict(value) for key, value in snapshot.get("points", {}).items()}
    total_algorithm_units = 0.0
    completed_algorithm_units = 0.0
    algorithms_per_point = 0
    for point in points.values():
        total_algorithms = float(point.get("total_algorithms", len(point.get("completed_algorithms", [])) or 0))
        if total_algorithms <= 0.0:
            total_algorithms = float(len(point.get("completed_algorithms", [])))
        total_algorithm_units += total_algorithms
        completed_algorithm_units += compute_point_algorithm_units(point)
        algorithms_per_point = max(algorithms_per_point, int(total_algorithms))
    enriched["points"] = points
    enriched["completed_algorithm_units"] = float(snapshot.get("completed_algorithm_units", completed_algorithm_units))
    enriched["total_algorithm_units"] = float(snapshot.get("total_algorithm_units", total_algorithm_units))
    enriched["algorithms_per_point"] = int(snapshot.get("algorithms_per_point", algorithms_per_point))
    return enriched


def format_split_progress_snapshot(snapshot: Mapping[str, Any]) -> str:
    """Format one split-run progress snapshot for terminal display.

    Args:
        snapshot: Collected split snapshot.

    Returns:
        A multi-line human-readable progress block.
    """

    enriched = enrich_split_snapshot(snapshot)
    lines = [
        (
            f"Exp-1 state={enriched.get('state', 'unknown')} "
            f"points={enriched.get('completed_points', 0)}/{enriched.get('total_points', 0)} "
            f"algorithms_per_point={enriched.get('algorithms_per_point', 0)} "
            f"algorithm_runs={enriched['completed_algorithm_units']:.2f}/{max(enriched['total_algorithm_units'], 1.0):.0f}"
        )
    ]
    updated_at = enriched.get("updated_at")
    if updated_at is not None:
        lines.append(f"Updated: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(float(updated_at)))}")
    for point_value in sorted(enriched["points"], key=lambda value: int(value)):
        point = enriched["points"][point_value]
        current_algorithm = point.get("current_algorithm") or "-"
        algorithm_index = point.get("algorithm_index") or max(0, len(point.get("completed_algorithms", [])))
        total_algorithms = point.get("total_algorithms") or enriched.get("algorithms_per_point", 0)
        last_event = point.get("last_event") or {}
        phase = last_event.get("phase") or point.get("state") or "waiting"
        detail = last_event.get("detail") or "-"
        completed_algorithms = ",".join(point.get("completed_algorithms", [])) or "-"
        lines.append(
            f"|Γ|={point_value} done={completed_algorithms} algo={algorithm_index}/{total_algorithms}:{current_algorithm} phase={phase} detail={detail}"
        )
    lines.append(f"Overall {render_progress_bar(enriched['completed_algorithm_units'], max(enriched['total_algorithm_units'], 1.0))}")
    return "\n".join(lines)


def render_terminal_progress_block(rendered_snapshot: str, overwrite: bool) -> str:
    """Wrap one rendered progress block for terminal output.

    Args:
        rendered_snapshot: Human-readable multi-line progress text.
        overwrite: Whether the block should clear and replace prior terminal content.

    Returns:
        The terminal-ready block string.
    """

    if overwrite:
        return f"\x1b[2J\x1b[H{rendered_snapshot}"
    return rendered_snapshot


def resolve_progress_mode(mode: ProgressMode) -> Literal["overwrite", "append"]:
    """Resolve one user-facing progress mode into a concrete rendering mode.

    Args:
        mode: Requested progress mode.

    Returns:
        The concrete rendering mode used by the split launcher.
    """

    if mode == "append":
        return "append"
    if mode == "overwrite":
        return "overwrite"
    return "overwrite"


def build_point_progress_snapshot(
    num_parcels: int,
    algorithm: str,
    algorithm_index: int,
    total_algorithms: int,
    completed_algorithms: list[str],
    state: str,
    last_event: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one normalized point-level progress snapshot.

    Args:
        num_parcels: Current parcel-count point.
        algorithm: Active algorithm name.
        algorithm_index: One-based active algorithm index.
        total_algorithms: Number of algorithms in this point.
        completed_algorithms: Fully completed algorithms for this point.
        state: Current point state.
        last_event: Optional latest algorithm progress event.

    Returns:
        The normalized point progress payload.
    """

    return {
        "state": state,
        "num_parcels": int(num_parcels),
        "current_algorithm": algorithm,
        "algorithm_index": int(algorithm_index),
        "total_algorithms": int(total_algorithms),
        "completed_algorithms": list(completed_algorithms),
        "last_event": dict(last_event or {}),
        "updated_at": time.time(),
    }
