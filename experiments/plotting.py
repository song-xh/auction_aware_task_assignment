"""Plotting helpers for unified sweep and comparison experiment outputs."""

from __future__ import annotations

import math
from decimal import Decimal
from pathlib import Path
from typing import Any, Sequence


PLOT_METRICS = ("TR", "CR", "BPT")
DEFAULT_COMPARISON_FIGSIZE = (5.4, 4.4)

ALGORITHM_STYLE: dict[str, dict[str, Any]] = {
    "rlcapa":  {"label": "RL-CAPA", "marker": "P", "color": "g",          "linestyle": "-",  "markersize": 13},
    "capa":    {"label": "CAPA",    "marker": "*", "color": "black",      "linestyle": "--", "markersize": 14},
    "ramcom":  {"label": "RAMCOM",  "marker": "s", "color": "r",          "linestyle": "-",  "markersize": 12},
    "impgta":  {"label": "ImpGTA",  "marker": "D", "color": "c",          "linestyle": "-",  "markersize": 12},
    "basegta": {"label": "BaseGTA", "marker": "v", "color": "b",          "linestyle": "-",  "markersize": 12},
    "mra":     {"label": "MRA",     "marker": "o", "color": "darkorange", "linestyle": "-",  "markersize": 12},
    "greedy":  {"label": "Greedy",  "marker": "x", "color": "m",          "linestyle": "-",  "markersize": 12},
}

BAR_STYLE: dict[str, dict[str, str]] = {
    "capa": {"facecolor": "orangered", "hatch": "/"},
    "impgta": {"facecolor": "yellowgreen", "hatch": "\\"},
    "ramcom": {"facecolor": "moccasin", "hatch": "-"},
    "rlcapa": {"facecolor": "deepskyblue", "hatch": "//"},
    "basegta": {"facecolor": "violet", "hatch": "\\\\"},
    "mra": {"facecolor": "#D3D3D3", "hatch": "-\\"},
    "greedy": {"facecolor": "peachpuff", "hatch": "x"},
}

METRIC_LABEL = {
    "TR":  "Total Revenue",
    "CR":  "Completion Rate",
    "BPT": "Batch Process Time",
}

XLABEL_OVERRIDE = {
    "num_parcels":      r"Number of Parcels $\Gamma$",
    "local_couriers":   r"Number of Local Couriers $\mathcal{C}$",
    "service_radius":   r"Service Radius $r$ (km)",
    "platforms":        r"Number of Platforms $\mathcal{P}$",
    "courier_capacity": r"Courier Capacity $\kappa$",
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

    Cross-platform fallback chain: real ``Times New Roman`` (Win/macOS/core
    fonts) → ``Nimbus Roman`` (URW PostScript Times clone) → ``Liberation
    Serif`` → ``DejaVu Serif`` (matplotlib bundled).

    Math symbols use the ``stix`` fontset, which is metric-compatible with Times
    and ensures characters like ``|Γ|``, ``×10⁵``, Greek letters, etc. share the
    same look as the surrounding text — so the entire plot is visually
    Times-family even when the literal ``Times New Roman`` file is absent.
    """

    import matplotlib.pyplot as plt

    serif_chain = [
        "Times New Roman",
        "Nimbus Roman",
        "Liberation Serif",
        "DejaVu Serif",
        "serif",
    ]
    plt.rcParams["font.family"] = serif_chain
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
    plt.rcParams["mathtext.it"] = "serif"
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
    use_bar = sweep_parameter == "platforms"
    for metric_name in PLOT_METRICS:
        if use_bar:
            visible_algorithms = visible_algorithms_for_bar(metric_name, algorithms)
        else:
            visible_algorithms = visible_algorithms_for_metric(metric_name, algorithms)
        series = [
            (algorithm, [run[algorithm]["metrics"][metric_name] for run in runs])
            for algorithm in visible_algorithms
        ]
        output_path = output_dir / f"{metric_name.lower()}_vs_{sweep_parameter}.png"
        if use_bar:
            _save_grouped_bar_plot(
                x_values=x_values,
                series=series,
                x_label=sweep_parameter,
                metric_name=metric_name,
                output_path=output_path,
            )
        else:
            _save_line_plot(
                x_values=x_values,
                series=series,
                x_label=sweep_parameter,
                metric_name=metric_name,
                output_path=output_path,
            )


def visible_algorithms_for_bar(metric_name: str, algorithms: Sequence[str]) -> list[str]:
    """Bar-plot variant: hide low-performing baselines and BaseGTA for exp4."""
    hidden = {"basegta", "mra", "greedy"}
    return [a for a in algorithms if a not in hidden]


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
        figure = plt.figure(figsize=DEFAULT_COMPARISON_FIGSIZE)
        ax = plt.gca()
        for spine in ax.spines.values():
            spine.set_linewidth(1.5)
        ax.bar(labels, [float(v) for v in values], color=colors, edgecolor="black")
        ax.set_xlabel("Algorithm", fontsize=20)
        plt.xticks(fontsize=16, rotation=20)
        plt.yticks(fontsize=18)
        y_exponent = _apply_scientific_y_formatter(ax)
        ax.set_ylabel(_axis_label_with_exponent(METRIC_LABEL.get(metric_name, metric_name), y_exponent), fontsize=20)
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
    figure = plt.figure(figsize=(7, 5))
    ax = plt.gca()
    for spine in ax.spines.values():
        spine.set_linewidth(1.5)

    x_positions = list(range(len(x_values)))
    numeric_x_values, use_numeric_axis = _coerce_numeric_x(x_values)
    scaled_x_labels: list[str] = []
    x_exponent = 0
    if use_numeric_axis:
        scaled_x_values, x_exponent = _scale_by_smallest_scientific_exponent(numeric_x_values)
        scaled_x_labels = [_format_scaled_tick(value) for value in scaled_x_values]
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
    ax.set_xlabel(_axis_label_with_exponent(xlabel, x_exponent if use_numeric_axis else 0), fontsize=20)

    ax.set_xticks(x_positions)
    if use_numeric_axis:
        ax.set_xticklabels(scaled_x_labels, fontsize=18)
        for label in ax.get_xticklabels():
            label.set_rotation(0)
            label.set_horizontalalignment("center")
            label.set_rotation_mode("default")
    else:
        ax.set_xticklabels(
            [_format_xtick(v) for v in x_values],
            fontsize=16,
            rotation=20,
            ha="right",
            rotation_mode="anchor",
        )
    ax.tick_params(axis="y", labelsize=18)
    y_exponent = _apply_scientific_y_formatter(ax)
    ax.set_ylabel(_axis_label_with_exponent(ylabel, y_exponent), fontsize=20)
    if x_positions:
        x_lo, x_hi = min(x_positions), max(x_positions)
        if x_lo == x_hi:
            x_lo, x_hi = x_lo - 0.5, x_hi + 0.5
        ax.set_xlim(x_lo, x_hi)
        ax.margins(x=0)

    if len(series) > 1:
        ax.legend(loc="best", fontsize=12, ncol=2, frameon=False)

    _set_axis_offset_text(ax.xaxis, 0, fontsize=16)
    figure.savefig(output_path, bbox_inches="tight", dpi=300)
    eps_path = output_path.with_suffix(".eps")
    try:
        figure.savefig(eps_path, bbox_inches="tight", dpi=300)
    except Exception:
        pass
    plt.close(figure)


def _save_grouped_bar_plot(
    x_values: Sequence[float],
    series: Sequence[tuple[str, Sequence[float]]],
    x_label: str,
    metric_name: str,
    output_path: Path,
) -> None:
    """Render grouped bar plots in the paper's filled-bar + hatch style."""
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches

    if not x_values or not series:
        return

    _apply_rc()
    figure = plt.figure(figsize=(8.4, 5.6))
    ax = plt.gca()
    for spine in ax.spines.values():
        spine.set_linewidth(1.5)

    n_groups = len(x_values)
    n_series = len(series)
    bar_width = 0.14
    group_width = bar_width * n_series
    group_gap = bar_width
    step = group_width + group_gap
    indices = [index * step for index in range(n_groups)]

    legend_handles: list[Any] = []
    for idx, (algo_name, ys) in enumerate(series):
        style = ALGORITHM_STYLE.get(algo_name, {"label": algo_name})
        bar_style = BAR_STYLE.get(algo_name, {"facecolor": "lightgray", "hatch": "/"})
        offsets = [i - group_width / 2 + bar_width * (idx + 0.5) for i in indices]
        ax.bar(
            offsets,
            [float(v) for v in ys],
            width=bar_width,
            color=bar_style["facecolor"],
            edgecolor="black",
            linewidth=1.5,
            hatch=bar_style["hatch"],
            label=style["label"],
        )
        legend_handles.append(
            mpatches.Patch(
                facecolor=bar_style["facecolor"],
                edgecolor="black",
                linewidth=1.5,
                hatch=bar_style["hatch"],
                label=style["label"],
            )
        )

    xlabel = XLABEL_OVERRIDE.get(x_label, x_label)
    ylabel = METRIC_LABEL.get(metric_name, metric_name)
    ax.set_xticks(indices)
    numeric_x_values, use_numeric_axis = _coerce_numeric_x(x_values)
    x_exponent = 0
    if use_numeric_axis:
        scaled_x_values, x_exponent = _scale_by_smallest_scientific_exponent(numeric_x_values)
        ax.set_xticklabels([_format_scaled_tick(value) for value in scaled_x_values], fontsize=25)
    else:
        ax.set_xticklabels([_format_xtick(v) for v in x_values], fontsize=25)
    ax.set_xlabel(_axis_label_with_exponent(xlabel, x_exponent if use_numeric_axis else 0), fontsize=25)
    ax.tick_params(axis="y", labelsize=25)
    y_exponent = _apply_scientific_y_formatter(ax)
    ax.set_ylabel(_axis_label_with_exponent(ylabel, y_exponent), fontsize=25)
    ax.set_xlim(
        indices[0] - group_width / 2 - bar_width,
        indices[-1] + group_width / 2 + bar_width,
    )
    ax.margins(x=0)

    ax.legend(
        handles=legend_handles,
        loc="upper center",
        ncol=min(n_series, 4),
        fontsize=18,
        frameon=False,
        handletextpad=0.5,
        columnspacing=0.9,
    )

    figure.tight_layout()
    _set_axis_offset_text(ax.xaxis, 0, fontsize=18)
    figure.savefig(output_path, bbox_inches="tight", dpi=300)
    eps_path = output_path.with_suffix(".eps")
    try:
        figure.savefig(eps_path, bbox_inches="tight", dpi=300)
    except Exception:
        pass
    plt.close(figure)


def _apply_scientific_y_formatter(ax: Any) -> int:
    """Render y ticks with integer mantissas and return the shared exponent."""

    return _apply_integer_scientific_axis_formatter(ax, "y")


def _apply_integer_scientific_axis_formatter(ax: Any, axis: str) -> int:
    """Format one axis as integer mantissas with a shared power-of-ten offset.

    Args:
        ax: Matplotlib axes object whose numeric axis should be formatted.
        axis: Axis selector, either `"x"` or `"y"`.

    Returns:
        Shared exponent used by the axis label. The selected axis is rewritten
        to fixed tick labels and the corner offset text is hidden.
    """

    if axis not in {"x", "y"}:
        raise ValueError(f"Unsupported axis for scientific formatting: {axis}")

    ax.figure.canvas.draw()
    target_axis = ax.xaxis if axis == "x" else ax.yaxis
    ticks = [float(value) for value in target_axis.get_majorticklocs() if math.isfinite(value)]
    exponent = _shared_integer_exponent(ticks)
    divisor = 10 ** exponent
    labels = [_format_scaled_tick(value / divisor) for value in ticks]
    if axis == "x":
        ax.set_xticks(ticks)
        ax.set_xticklabels(labels, fontsize=18)
    else:
        ax.set_yticks(ticks)
        ax.set_yticklabels(labels, fontsize=18)
    _set_axis_offset_text(target_axis, 0, fontsize=16 if axis == "x" else 18)
    return exponent


def _axis_label_with_exponent(label: str, exponent: int) -> str:
    """Append one shared scientific multiplier beside an axis title.

    Args:
        label: Base axis title.
        exponent: Shared base-10 exponent for the axis values.

    Returns:
        Axis title with multiplier suffix when needed.
    """

    if exponent == 0:
        return label
    return rf"{label} ($\times10^{{{exponent}}}$)"


def _set_axis_offset_text(axis: Any, exponent: int, fontsize: int) -> None:
    """Set a fixed scientific offset label on one axis.

    Args:
        axis: Matplotlib axis object.
        exponent: Shared base-10 exponent to display.
        fontsize: Font size for the offset text.

    Returns:
        None. The axis offset text is updated in place.
    """

    offset_text = axis.get_offset_text()
    offset_text.set_text("" if exponent == 0 else rf"$\times10^{{{exponent}}}$")
    offset_text.set_fontsize(fontsize)
    offset_text.set_visible(exponent != 0)


def _scale_by_smallest_scientific_exponent(values: Sequence[float]) -> tuple[list[float], int]:
    """Scale coordinates by the largest shared power-of-ten integer factor.

    Args:
        values: Numeric coordinate values.

    Returns:
        A pair of scaled coordinates and the base-10 exponent that was factored
        out. The chosen exponent keeps all scaled values as integers whenever a
        shared power-of-ten factor exists. For example, `[1000, 2200, 5000]`
        returns `([10, 22, 50], 2)`.
    """

    exponent = _shared_integer_exponent(values)
    if exponent == 0 and not any(math.isfinite(value) and value != 0 for value in values):
        return list(values), 0
    divisor = 10 ** exponent
    return [value / divisor for value in values], exponent


def _shared_integer_exponent(values: Sequence[float]) -> int:
    """Return the shared power-of-ten factor that preserves integer mantissas.

    Args:
        values: Numeric values that will share one scientific multiplier.

    Returns:
        Largest integer exponent `e` such that each finite nonzero value divided
        by `10^e` is an integer within the decimal precision implied by its
        textual representation.
    """

    exponents = [
        _integer_power_of_ten_exponent(value)
        for value in values
        if math.isfinite(value) and value != 0
    ]
    if not exponents:
        return 0
    return min(exponents)


def _integer_power_of_ten_exponent(value: float) -> int:
    """Return the largest power-of-ten factor embedded in one decimal value.

    Args:
        value: Numeric value to analyze.

    Returns:
        Largest integer exponent `e` such that `value / 10^e` remains an
        integer under the value's finite decimal representation.
    """

    decimal_value = Decimal(format(abs(value), ".12g"))
    digits = decimal_value.as_tuple().digits
    trailing_zeros = 0
    for digit in reversed(digits):
        if digit != 0:
            break
        trailing_zeros += 1
    return decimal_value.as_tuple().exponent + trailing_zeros


def _format_scaled_tick(value: float) -> str:
    """Format a scaled coordinate tick compactly.

    Args:
        value: Scaled coordinate value.

    Returns:
        Integer-looking values without decimals, otherwise a compact decimal.
    """

    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return f"{value:g}"


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
    """Compact numeric tick label without K-suffix shorthand."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    if f.is_integer():
        return str(int(f))
    return f"{f:g}"
