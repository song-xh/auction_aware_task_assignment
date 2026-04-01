"""Plotting helpers for unified sweep and comparison experiment outputs."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence


PLOT_METRICS = ("TR", "CR", "BPT")


def save_single_algorithm_plots(summary: dict[str, Any], output_dir: Path) -> None:
    """Write one plot per paper metric for a single-algorithm sweep summary."""
    algorithm = str(summary["algorithm"])
    sweep_parameter = str(summary["sweep_parameter"])
    runs = list(summary.get("runs", []))
    x_values = [run[sweep_parameter] for run in runs]
    for metric_name in PLOT_METRICS:
        y_values = [run[algorithm]["metrics"][metric_name] for run in runs]
        _save_line_plot(
            x_values=x_values,
            series=[(algorithm, y_values)],
            x_label=sweep_parameter,
            y_label=metric_name,
            output_path=output_dir / f"{metric_name.lower()}_vs_{sweep_parameter}.png",
        )


def save_comparison_plots(summary: dict[str, Any], output_dir: Path) -> None:
    """Write one comparison plot per paper metric for a multi-algorithm sweep summary."""
    algorithms = [str(name) for name in summary.get("algorithms", [])]
    sweep_parameter = str(summary["sweep_parameter"])
    runs = list(summary.get("runs", []))
    x_values = [run[sweep_parameter] for run in runs]
    for metric_name in PLOT_METRICS:
        series = [
            (algorithm, [run[algorithm]["metrics"][metric_name] for run in runs])
            for algorithm in algorithms
        ]
        _save_line_plot(
            x_values=x_values,
            series=series,
            x_label=sweep_parameter,
            y_label=metric_name,
            output_path=output_dir / f"{metric_name.lower()}_vs_{sweep_parameter}.png",
        )


def _save_line_plot(
    x_values: Sequence[float],
    series: Sequence[tuple[str, Sequence[float]]],
    x_label: str,
    y_label: str,
    output_path: Path,
) -> None:
    """Render a compact multi-series line plot to the given file path."""
    import matplotlib.pyplot as plt

    if not x_values:
        return
    plt.figure(figsize=(8, 5))
    for label, y_values in series:
        plt.plot(x_values, y_values, marker="o", label=label)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.grid(True, linestyle="--", linewidth=0.5, alpha=0.5)
    if len(series) > 1:
        plt.legend()
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
