"""Plot helpers for RL-CAPA ablation comparisons."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence

from rl_capa.visualize import _configure_matplotlib_cache, smooth


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
    import matplotlib.pyplot as plt

    normalized_output_path = Path(output_path)
    normalized_output_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 6))
    colors = {
        "rl-capa": "tab:blue",
        "rl-capa-stage1": "tab:orange",
        "rl-capa-stage2": "tab:green",
    }
    for name, rewards in reward_histories.items():
        reward_values = [float(value) for value in rewards]
        episodes = list(range(1, len(reward_values) + 1))
        color = colors.get(name)
        ax.plot(episodes, reward_values, color=color, alpha=0.25, linewidth=0.8)
        ax.plot(
            episodes,
            smooth(reward_values, window=window),
            color=color,
            linewidth=1.8,
            label=name,
        )
    ax.set_title("RL-CAPA Ablation Reward Curves")
    ax.set_xlabel("Episode")
    ax.set_ylabel("Episode Reward")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(str(normalized_output_path), dpi=150)
    plt.close(fig)
    return normalized_output_path
