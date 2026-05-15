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
    "BPT": "Batch Process Time",
}

XLABEL_OVERRIDE = {
    "num_parcels":     r"Number of Parcels $|\Gamma|$",
    "local_couriers":  r"Number of Couriers $|C|$",
    "service_radius":  r"Service Radius (km)",
    "platforms":       r"Number of Platforms",
    "courier_capacity": r"Courier Capacity",
}


def visible_algorithms_for_metric(metric_name: str, algorithms: Sequence[str]) -> list[str]:
    """Return algorithms that should be visible for one paper metric plot.

    Args:
        metric_name: Paper metric identifier, e.g. `TR`, `CR`, or `BPT`.
        algorithms: Candidate algorithm names in display order.

    Returns:
        Ordered algorithm names after applying review-requested filtering.
    """

    hidden = {"basegta"}
    if metric_name == "BPT":
        hidden.add("mra")
    return [algorithm for algorithm in algorithms if algorithm not in hidden]


def _apply_rc() -> None:
    """Configure matplotlib to render every text element (axis labels, ticks,
    legends, math symbols) in Times New Roman.

    Cross-platform fallback chain: real ``Times New Roman`` (Win/macOS) →
    ``Tinos`` (Google open-source Times-metric clone, Linux) → ``Nimbus Roman``
    (URW PostScript Times clone) → ``DejaVu Serif`` (matplotlib bundled).

    Math symbols use the ``stix`` fontset, which is metric-compatible with Times
    and ensures characters like ``|P|``, ``×10⁵``, Greek letters, etc. share the
    same look as the surrounding text — so the entire plot is visually
    Times-family even when the literal ``Times New Roman`` file is absent.
    """

    import matplotlib.pyplot as plt

    serif_chain = [
        "Times New Roman",
        "Tinos",
        "Nimbus Roman",
        "Nimbus Roman No9 L",
        "Liberation Serif",
        "DejaVu Serif",
        "serif",
    ]
    plt.rcParams["font.family"] = "serif"
    plt.rcParams["font.serif"] = serif_chain
    plt.rcParams["mathtext.fontset"] = "stix"
    plt.rcParams["mathtext.default"] = "rm"
    plt.rcParams["pdf.fonttype"] = 42
    plt.rcParams["ps.fonttype"] = 42
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["xtick.labelsize"] = 18
    plt.rcParams["ytick.labelsize"] = 18
    plt.rcParams["legend.fontsize"] = 12
    # Force every text element (axis labels, tick labels, math symbols, legends)
    # through the Times-family serif chain configured above. Without this,
    # matplotlib backends sometimes fall back to DejaVu Sans for tick labels
    # even when font.family=serif is set globally.
    plt.rcParams["mathtext.rm"] = "serif"
    plt.rcParams["mathtext.it"] = "serif:italic"
    plt.rcParams["mathtext.bf"] = "serif:bold"


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
        visible_algorithms = visible_algorithms_for_metric(metric_name, algorithms)
        series = [
            (algorithm, [run[algorithm]["metrics"][metric_name] for run in runs])
            for algorithm in visible_algorithms
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
        visible_algorithms = visible_algorithms_for_metric(metric_name, algorithms)
        values = [results[algorithm]["metrics"][metric_name] for algorithm in visible_algorithms]
        labels = [ALGORITHM_STYLE.get(a, {}).get("label", a) for a in visible_algorithms]
        colors = [ALGORITHM_STYLE.get(a, {}).get("color", "gray") for a in visible_algorithms]
        figure = plt.figure(figsize=(6, 5))
        ax = plt.gca()
        for spine in ax.spines.values():
            spine.set_linewidth(1.5)
        ax.bar(labels, [float(v) for v in values], color=colors, edgecolor="black")
        ax.set_xlabel("Algorithm", fontsize=20)
        ax.set_ylabel(METRIC_LABEL.get(metric_name, metric_name), fontsize=20)
        plt.xticks(fontsize=16, rotation=20)
        plt.yticks(fontsize=18)
        _apply_scientific_y_formatter(ax)
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

    numeric_x, use_numeric_axis = _coerce_numeric_x(x_values)
    x_positions = numeric_x if use_numeric_axis else list(range(1, len(x_values) + 1))
    # Use a log x-axis when the sweep spans more than one decade and every
    # value is strictly positive. Otherwise linear spacing already reflects
    # the magnitudes adequately.
    use_log_x = (
        use_numeric_axis
        and all(v > 0 for v in x_positions)
        and len(x_positions) >= 2
        and (max(x_positions) / min(x_positions)) >= 10.0
    )
    if use_log_x:
        ax.set_xscale("log")
    for algo_name, ys in series:
        style = ALGORITHM_STYLE.get(algo_name, {
            "label": algo_name, "marker": "o", "color": "gray",
            "linestyle": "-", "markersize": 10,
        })
        ax.plot(
            x_positions,
            [float(v) for v in ys],
            label=style["label"],
            marker=style["marker"],
            markerfacecolor="none",
            color=style["color"],
            linewidth=3,
            markersize=style["markersize"],
            linestyle=style["linestyle"],
        )

    xlabel = XLABEL_OVERRIDE.get(x_label, x_label)
    ylabel = METRIC_LABEL.get(metric_name, metric_name)
    ax.set_xlabel(xlabel, fontsize=20)
    ax.set_ylabel(ylabel, fontsize=20)

    tick_labels = [_format_tick_scientific(v) for v in x_values]
    ax.set_xticks(x_positions)
    rotation = 0 if use_log_x else 20
    ha = "center" if use_log_x else "right"
    ax.set_xticklabels(
        tick_labels,
        fontsize=16,
        rotation=rotation,
        ha=ha,
        rotation_mode="anchor" if rotation else "default",
    )
    if use_log_x:
        ax.minorticks_off()
    ax.tick_params(axis="y", labelsize=18)
    _apply_scientific_y_formatter(ax)
    if x_positions:
        x_lo, x_hi = min(x_positions), max(x_positions)
        if x_lo == x_hi:
            x_lo, x_hi = x_lo - 1, x_hi + 1
        if use_log_x:
            pad = (x_hi / x_lo) ** 0.04
            ax.set_xlim(x_lo / pad, x_hi * pad)
        elif use_numeric_axis:
            pad = (x_hi - x_lo) * 0.03
            ax.set_xlim(x_lo - pad, x_hi + pad)
        else:
            ax.set_xlim(x_lo, x_hi)

    if len(series) > 1:
        ax.legend(loc="best", fontsize=12, ncol=2, frameon=False)

    figure.savefig(output_path, bbox_inches="tight", dpi=300)
    eps_path = output_path.with_suffix(".eps")
    try:
        figure.savefig(eps_path, bbox_inches="tight", dpi=300)
    except Exception:
        pass
    plt.close(figure)


def _apply_scientific_y_formatter(ax: Any) -> None:
    """Force the y-axis to render every tick label in scientific notation.

    Uses `ScalarFormatter(useMathText=True)` with the scientific power limits
    pinned to `(0, 0)` so even values within the default `[10^-3, 10^3]` band
    are rendered as `a×10^b` rather than plain decimals. The exponent is shown
    as a regular tick label, not as a corner annotation.
    """

    from matplotlib.ticker import ScalarFormatter

    formatter = ScalarFormatter(useMathText=True, useOffset=False)
    formatter.set_scientific(True)
    formatter.set_powerlimits((0, 0))
    ax.yaxis.set_major_formatter(formatter)
    ax.ticklabel_format(axis="y", style="sci", scilimits=(0, 0), useMathText=True)


def _format_tick_scientific(value: Any) -> str:
    """Render one tick value as `a×10^b` (or just `0` for the zero crossing).

    Used for x-axis tick labels because they are set manually via
    `set_xticklabels`, which bypasses matplotlib's `ScalarFormatter`.
    """

    try:
        f = float(value)
    except (TypeError, ValueError):
        return str(value)
    if f == 0.0 or not math.isfinite(f):
        return "0" if f == 0.0 else str(value)
    exponent = int(math.floor(math.log10(abs(f))))
    mantissa = f / (10 ** exponent)
    if abs(mantissa - round(mantissa)) < 1e-9:
        mantissa_str = f"{int(round(mantissa))}"
    else:
        mantissa_str = f"{mantissa:.1f}".rstrip("0").rstrip(".")
    return rf"${mantissa_str}\times10^{{{exponent}}}$"


def _coerce_numeric_x(x_values: Sequence[Any]) -> tuple[list[float], bool]:
    """Try to interpret sweep x-values as numeric for adaptive axis spacing.

    Returns the converted list and a flag indicating whether numeric placement
    should actually be used. If any value cannot be converted to float (e.g.
    categorical sweeps) we fall back to evenly spaced indices upstream.
    """

    coerced: list[float] = []
    for value in x_values:
        try:
            coerced.append(float(value))
        except (TypeError, ValueError):
            return [], False
    return coerced, True


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
