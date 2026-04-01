"""Predefined paper-style experiment suites for the unified Chengdu runner."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Sequence

from .compare import run_comparison_sweep
from .paper_config import PAPER_SUITE_PRESETS


def run_experiment_suite(
    suite_name: str,
    preset_name: str,
    algorithms: Sequence[str],
    output_dir: Path,
    fixed_config: dict[str, Any],
    comparison_runner: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run a predefined collection of sweeps and persist a suite manifest.

    Args:
        suite_name: Name of the predefined suite.
        preset_name: Named preset defining the axis grid for this suite.
        algorithms: Algorithms compared at each suite point.
        output_dir: Directory that receives per-axis outputs and the suite manifest.
        fixed_config: Base configuration shared across all axes.
        comparison_runner: Optional injected comparison runner for tests.

    Returns:
        A suite summary manifest keyed by sweep axis.
    """

    runner = comparison_runner or run_comparison_sweep
    output_dir.mkdir(parents=True, exist_ok=True)
    axes = _get_suite_axes(suite_name, preset_name)
    results: dict[str, Any] = {}
    for axis_name, values in axes.items():
        axis_output_dir = output_dir / axis_name
        results[axis_name] = runner(
            algorithms=algorithms,
            output_dir=axis_output_dir,
            sweep_parameter=axis_name,
            sweep_values=values,
            fixed_config=fixed_config,
        )
    summary = {
        "suite": suite_name,
        "preset": preset_name,
        "algorithms": list(algorithms),
        "results": results,
    }
    with (output_dir / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
    return summary


def _get_suite_axes(suite_name: str, preset_name: str) -> dict[str, list[float]]:
    """Return the predefined sweep axes for one supported suite and preset combination."""
    if suite_name not in PAPER_SUITE_PRESETS:
        raise ValueError(f"Unsupported experiment suite `{suite_name}`.")
    suite_presets = PAPER_SUITE_PRESETS[suite_name]
    if preset_name not in suite_presets:
        raise ValueError(f"Unsupported preset `{preset_name}` for suite `{suite_name}`.")
    return suite_presets[preset_name]
