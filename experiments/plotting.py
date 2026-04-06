"""Plotting helpers for unified sweep and comparison experiment outputs."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence


PLOT_METRICS = ("TR", "CR", "BPT")
SERIES_MARKERS = ("o", "s", "^", "D", "v", "P", "X", "*")
SERIES_COLORS = (
    "#1f77b4",
    "#ff7f0e",
    "#2ca02c",
    "#d62728",
    "#9467bd",
    "#8c564b",
    "#e377c2",
    "#7f7f7f",
)


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


def save_default_comparison_plots(summary: dict[str, Any], output_dir: Path) -> None:
    """Write one categorical comparison plot per paper metric for the default-setting experiment."""
    import matplotlib.pyplot as plt

    algorithms = [str(name) for name in summary.get("algorithms", [])]
    results = dict(summary.get("results", {}))
    if not algorithms:
        return
    for metric_name in PLOT_METRICS:
        values = [results[algorithm]["metrics"][metric_name] for algorithm in algorithms]
        plt.figure(figsize=(8, 5))
        plt.bar(algorithms, values)
        plt.xlabel("algorithm")
        plt.ylabel(metric_name)
        plt.grid(True, axis="y", linestyle="--", linewidth=0.5, alpha=0.5)
        plt.tight_layout()
        plt.savefig(output_dir / f"default_{metric_name.lower()}_comparison.png")
        plt.close()


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
    figure, axis = plt.subplots(figsize=(9, 5.6))
    for index, (label, y_values) in enumerate(series):
        marker = SERIES_MARKERS[index % len(SERIES_MARKERS)]
        color = SERIES_COLORS[index % len(SERIES_COLORS)]
        axis.plot(
            x_values,
            y_values,
            marker=marker,
            markersize=7,
            linewidth=2,
            color=color,
            label=label,
        )
    axis.set_xlabel(x_label)
    axis.set_ylabel(y_label)
    axis.set_xticks(list(x_values))
    axis.grid(True, linestyle="--", linewidth=0.6, alpha=0.45)
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    if len(series) > 1:
        axis.legend(loc="best", frameon=False, ncols=2)
    figure.tight_layout()
    figure.savefig(output_path, dpi=180)
    plt.close(figure)
