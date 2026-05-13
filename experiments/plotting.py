"""Plotting helpers for unified sweep and comparison experiment outputs."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Sequence


PLOT_METRICS = ("TR", "CR", "BPT")

ALGORITHM_STYLE: dict[str, dict[str, Any]] = {
    "capa":    {"label": "CAPA",    "marker": "*", "color": "black",      "linestyle": "--", "markersize": 14},
    "ramcom":  {"label": "RAMCOM",  "marker": "s", "color": "r",          "linestyle": "-",  "markersize": 12},
    "impgta":  {"label": "ImpGTA",  "marker": "D", "color": "c",          "linestyle": "-",  "markersize": 12},
    "basegta": {"label": "BaseGTA", "marker": "v", "color": "b",          "linestyle": "-",  "markersize": 12},
    "mra":     {"label": "MRA",     "marker": "o", "color": "darkorange", "linestyle": "-",  "markersize": 12},
    "greedy":  {"label": "Greedy",  "marker": "x", "color": "m",          "linestyle": "-",  "markersize": 12},
}

METRIC_LABEL = {
    "TR":  "Total Revenue",
    "CR":  "Completion Rate",
    "BPT": "Balance Per Task",
}

XLABEL_OVERRIDE = {
    "num_parcels":     r"Number of Parcels $|P|$",
    "local_couriers":  r"Number of Couriers $|C|$",
    "service_radius":  r"Service Radius (km)",
    "platforms":       r"Number of Platforms",
    "courier_capacity": r"Courier Capacity",
}


def _apply_rc() -> None:
    import matplotlib.pyplot as plt

    plt.rcParams["font.family"] = ["Times New Roman", "DejaVu Serif", "serif"]
    plt.rcParams["mathtext.fontset"] = "custom"
    plt.rcParams["mathtext.rm"] = "Times New Roman"
    plt.rcParams["mathtext.it"] = "Times New Roman:italic"
    plt.rcParams["mathtext.bf"] = "Times New Roman:bold"


def _pick_scale(values: Sequence[float]) -> tuple[float, str]:
    """Return (divisor, ylabel-suffix) so scaled values fall in [1, 100)."""
    finite = [abs(v) for v in values if v is not None and math.isfinite(v) and v != 0]
    if not finite:
        return 1.0, ""
    vmax = max(finite)
    if vmax >= 1000:
        exp = int(math.floor(math.log10(vmax)))
        return 10 ** exp, rf" $\times 10^{{{exp}}}$"
    return 1.0, ""


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
            metric_name=metric_name,
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
            metric_name=metric_name,
            output_path=output_dir / f"{metric_name.lower()}_vs_{sweep_parameter}.png",
        )


def save_default_comparison_plots(summary: dict[str, Any], output_dir: Path) -> None:
    """Write one categorical comparison plot per paper metric for the default-setting experiment."""
    import matplotlib.pyplot as plt

    _apply_rc()
    algorithms = [str(name) for name in summary.get("algorithms", [])]
    results = dict(summary.get("results", {}))
    if not algorithms:
        return
    for metric_name in PLOT_METRICS:
        values = [results[algorithm]["metrics"][metric_name] for algorithm in algorithms]
        labels = [ALGORITHM_STYLE.get(a, {}).get("label", a) for a in algorithms]
        colors = [ALGORITHM_STYLE.get(a, {}).get("color", "gray") for a in algorithms]
        figure = plt.figure(figsize=(6, 5))
        ax = plt.gca()
        for spine in ax.spines.values():
            spine.set_linewidth(1.5)
        divisor, suffix = _pick_scale(values)
        ax.bar(labels, [v / divisor for v in values], color=colors, edgecolor="black")
        ax.set_xlabel("Algorithm", fontsize=20)
        ax.set_ylabel(METRIC_LABEL.get(metric_name, metric_name) + suffix, fontsize=20)
        plt.xticks(fontsize=16, rotation=20)
        plt.yticks(fontsize=18)
        figure.savefig(output_dir / f"default_{metric_name.lower()}_comparison.png",
                       bbox_inches="tight", dpi=300)
        plt.close(figure)


def _save_line_plot(
    x_values: Sequence[float],
    series: Sequence[tuple[str, Sequence[float]]],
    x_label: str,
    metric_name: str,
    output_path: Path,
) -> None:
    """Render a styled multi-series line plot matching the paper template."""
    import matplotlib.pyplot as plt

    if not x_values:
        return

    _apply_rc()
    figure = plt.figure(figsize=(6, 5))
    ax = plt.gca()
    for spine in ax.spines.values():
        spine.set_linewidth(1.5)

    all_y: list[float] = []
    for _, ys in series:
        all_y.extend(float(v) for v in ys if v is not None)
    divisor, suffix = _pick_scale(all_y)

    x_index = list(range(1, len(x_values) + 1))
    for algo_name, ys in series:
        style = ALGORITHM_STYLE.get(algo_name, {
            "label": algo_name, "marker": "o", "color": "gray",
            "linestyle": "-", "markersize": 10,
        })
        ax.plot(
            x_index,
            [float(v) / divisor for v in ys],
            label=style["label"],
            marker=style["marker"],
            markerfacecolor="none",
            color=style["color"],
            linewidth=3,
            markersize=style["markersize"],
            linestyle=style["linestyle"],
        )

    xlabel = XLABEL_OVERRIDE.get(x_label, x_label)
    ylabel = METRIC_LABEL.get(metric_name, metric_name) + suffix
    ax.set_xlabel(xlabel, fontsize=20)
    ax.set_ylabel(ylabel, fontsize=20)

    tick_labels = [_format_xtick(v) for v in x_values]
    ax.set_xticks(x_index)
    ax.set_xticklabels(tick_labels, fontsize=18)
    ax.tick_params(axis="y", labelsize=18)
    ax.set_xlim(min(x_index), max(x_index))

    if len(series) > 1:
        ax.legend(loc="best", fontsize=12, ncol=2, frameon=False)

    figure.savefig(output_path, bbox_inches="tight", dpi=300)
    eps_path = output_path.with_suffix(".eps")
    try:
        figure.savefig(eps_path, bbox_inches="tight", dpi=300)
    except Exception:
        pass
    plt.close(figure)


def _format_xtick(v: Any) -> str:
    """Compact tick label: 1000 -> '1.0K', floats kept short."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    if f >= 1000 and f.is_integer():
        return f"{f / 1000:.1f}K"
    if f.is_integer():
        return str(int(f))
    return f"{f:g}"
