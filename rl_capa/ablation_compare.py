"""Plot helpers for RL-CAPA ablation comparisons."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence

import numpy as np

from rl_capa.visualize import _configure_matplotlib_cache, add_legend_if_present, smooth, smooth_with_band


def _plot_publication_band(
    ax: object,
    episodes: Sequence[int],
    values: Sequence[float],
    *,
    color: str,
    label: str,
    window: int,
) -> None:
    """Plot one publication-style curve with a softened variability band.

    Args:
        ax: Matplotlib axes receiving the plot.
        episodes: Episode indices for the x-axis.
        values: Reward values already scaled for plotting.
        color: Curve and band color.
        label: Legend label for the curve.
        window: Rolling window size used for smoothing.
    """

    mean_curve, lower_curve, upper_curve = smooth_with_band(values, window=window)
    band_half_width = np.maximum(mean_curve - lower_curve, 0.0)
    softened_band = smooth(band_half_width, window=window)
    lower_band = mean_curve - softened_band
    upper_band = mean_curve + softened_band
    ax.fill_between(
        episodes,
        lower_band,
        upper_band,
        color=color,
        alpha=0.18,
        linewidth=0,
        zorder=2,
    )
    ax.plot(
        episodes,
        mean_curve,
        color=color,
        linewidth=1.6,
        label=label,
        zorder=3,
    )


def plot_reward_comparison(
    reward_histories: Mapping[str, Sequence[float]],
    output_path: str | Path,
    window: int = 25,
) -> Path:
    """Plot reward-vs-episode curves for RL-CAPA and ablation variants.

    Args:
        reward_histories: Mapping from variant name to episode reward sequence.
        output_path: Destination PNG path.
        window: Smoothing window for the overlaid trend line.

    Returns:
        Path to the saved plot.
    """

    _configure_matplotlib_cache()
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib import font_manager
    import matplotlib.pyplot as plt

    normalized_output_path = Path(output_path)
    normalized_output_path.parent.mkdir(parents=True, exist_ok=True)

    available_fonts = {font.name for font in font_manager.fontManager.ttflist}
    preferred_serif = "Times New Roman" if "Times New Roman" in available_fonts else "Nimbus Roman"
    plt.rcParams["font.family"] = [preferred_serif]
    plt.rcParams["font.serif"] = [
        "Times New Roman",
        "Nimbus Roman",
        "Nimbus Roman No9 L",
        "TeX Gyre Termes",
        "serif",
    ]
    plt.rcParams["mathtext.fontset"] = "custom"
    plt.rcParams["mathtext.rm"] = preferred_serif
    plt.rcParams["mathtext.it"] = f"{preferred_serif}:italic"
    plt.rcParams["mathtext.bf"] = f"{preferred_serif}:bold"
    plt.rcParams["mathtext.cal"] = preferred_serif

    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    colors = {
        "rl-capa": "#3B4CFF",
        "rl-capa-stage1": "#F5B02E",
        "rl-capa-stage2": "#2FA84F",
    }
    for name, rewards in reward_histories.items():
        reward_values = [float(value) / 100.0 for value in rewards]
        episodes = list(range(len(reward_values)))
        color = colors.get(name)
        _plot_publication_band(
            ax,
            episodes,
            reward_values,
            color=color,
            label=name,
            window=window,
        )

    ax.set_xlabel("Episodes", fontsize=18)
    ax.set_ylabel("Total Reward", fontsize=18)
    ax.set_xlim(0, 2000)
    ax.set_xticks([0, 500, 1000, 1500, 2000])
    ax.margins(x=0)
    ax.set_ylim(20.5, 32.2)
    ax.set_yticks([22, 24, 26, 28, 30, 32])
    ax.text(
        0.0,
        1.01,
        r"$\times 10^2$",
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=14,
    )
    ax.grid(True, color="#b0b0b0", alpha=0.25, linewidth=0.8)
    ax.tick_params(axis="both", which="major", labelsize=16, width=1.0, length=4)
    for spine in ax.spines.values():
        spine.set_linewidth(1.0)
    add_legend_if_present(
        ax,
        loc="lower right",
        ncol=1,
        frameon=False,
        fontsize=14,
        handlelength=2.8,
        borderaxespad=0.6,
    )

    pdf_output_path = normalized_output_path.with_suffix(".pdf")
    fig.tight_layout()
    fig.savefig(str(normalized_output_path), dpi=300, bbox_inches="tight")
    fig.savefig(str(pdf_output_path), bbox_inches="tight")
    plt.close(fig)
    return normalized_output_path
