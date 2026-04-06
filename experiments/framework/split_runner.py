"""Generic split-process seeded experiment runner shared by experiment wrappers."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from io import TextIOWrapper
from pathlib import Path
from typing import Any, Callable, Sequence

from rich.console import Console
from rich.live import Live

from experiments.monitor_split import collect_split_progress
from experiments.progress import (
    build_split_progress_renderable,
    format_split_progress_snapshot,
    render_terminal_progress_block,
    resolve_progress_mode,
)

from .models import ExperimentSplitSpec


def _point_token(value: int | float) -> str:
    """Build a filesystem-safe stable token for one sweep point value."""

    text = str(value)
    return text.replace("/", "_").replace(" ", "_")


def run_seeded_split_experiment(
    split_spec: ExperimentSplitSpec,
    point_command_builder: Callable[[int | float, Path], Sequence[str]],
    aggregate_summary_builder: Callable[[dict[int | float, Path]], dict[str, Any]],
) -> dict[str, Any]:
    """Run one seeded split-process experiment using generic point subprocesses.

    Args:
        split_spec: Split-level experiment specification.
        point_command_builder: Builds the subprocess command for one point.
        aggregate_summary_builder: Builds the final aggregate summary from completed point directories.

    Returns:
        Aggregate experiment summary.
    """

    split_spec.tmp_root.mkdir(parents=True, exist_ok=True)
    split_spec.output_dir.mkdir(parents=True, exist_ok=True)
    processes: dict[int | float, subprocess.Popen[str]] = {}
    log_handles: list[TextIOWrapper] = []
    point_output_dirs: dict[int | float, Path] = {}
    all_point_status: dict[str, Any] = {}
    resolved_progress_mode = resolve_progress_mode(split_spec.progress_mode)  # type: ignore[arg-type]
    overwrite_terminal = resolved_progress_mode == "overwrite"
    console = Console()
    live: Live | None = None
    try:
        if overwrite_terminal:
            live = Live(console=console, refresh_per_second=4, transient=False, auto_refresh=False)
            live.start()
        for value in split_spec.axis_values:
            point_output_dir = split_spec.tmp_root / f"point_{_point_token(value)}"
            if point_output_dir.exists():
                shutil.rmtree(point_output_dir)
            point_output_dirs[value] = point_output_dir
            point_output_dir.mkdir(parents=True, exist_ok=True)
            stdout_handle = (point_output_dir / "stdout.log").open("w", encoding="utf-8")
            stderr_handle = (point_output_dir / "stderr.log").open("w", encoding="utf-8")
            log_handles.extend([stdout_handle, stderr_handle])
            process = subprocess.Popen(
                list(point_command_builder(value, point_output_dir)),
                cwd=Path(__file__).resolve().parents[2],
                stdout=stdout_handle,
                stderr=stderr_handle,
                text=True,
            )
            processes[value] = process
            all_point_status[str(value)] = {
                "pid": process.pid,
                "returncode": None,
                "output_dir": str(point_output_dir),
                "total_algorithms": len(split_spec.algorithms),
            }

        status_path = split_spec.tmp_root / "split_status.json"
        while processes:
            finished: list[int] = []
            for value, process in processes.items():
                return_code = process.poll()
                all_point_status[str(value)] = {
                    "pid": process.pid,
                    "returncode": return_code,
                    "output_dir": str(point_output_dirs[value]),
                    "total_algorithms": len(split_spec.algorithms),
                }
                if return_code is not None:
                    finished.append(value)
            with status_path.open("w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "state": "running" if processes else "finished",
                        "experiment_label": split_spec.experiment_label,
                        "axis_name": split_spec.axis_name,
                        "points": all_point_status,
                        "updated_at": time.time(),
                    },
                    handle,
                    indent=2,
                )
            snapshot = collect_split_progress(split_spec.tmp_root)
            if overwrite_terminal:
                assert live is not None
                live.update(build_split_progress_renderable(snapshot), refresh=True)
            else:
                rendered = render_terminal_progress_block(
                    format_split_progress_snapshot(snapshot),
                    overwrite=False,
                )
                sys.stdout.write(f"{rendered}\n")
                sys.stdout.flush()
            if not finished:
                time.sleep(split_spec.poll_seconds)
                continue
            for value in finished:
                process = processes.pop(value)
                if process.returncode != 0:
                    raise RuntimeError(
                        f"Split experiment point {value} failed. See {point_output_dirs[value] / 'stderr.log'}"
                    )
        with status_path.open("w", encoding="utf-8") as handle:
            json.dump(
                {
                    "state": "finished",
                    "experiment_label": split_spec.experiment_label,
                    "axis_name": split_spec.axis_name,
                    "points": all_point_status,
                    "updated_at": time.time(),
                },
                handle,
                indent=2,
            )
        if overwrite_terminal:
            assert live is not None
            live.update(build_split_progress_renderable(collect_split_progress(split_spec.tmp_root)), refresh=True)
    finally:
        if live is not None:
            live.stop()
        for handle in log_handles:
            handle.close()
    return aggregate_summary_builder(point_output_dirs)
