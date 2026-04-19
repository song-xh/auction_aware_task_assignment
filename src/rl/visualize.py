"""Training curve visualization for RL-CAPA (spec Section 11).

Plots 7 curves with sliding-window smoothing (window=50):
  1. Episode Reward
  2. L_V1 (Critic 1 loss)
  3. L_V2 (Critic 2 loss)
  4. Policy Loss pi1
  5. Policy Loss pi2
  6. Batch Size Distribution (mean batch size per episode)
  7. Cross Rate (fraction of parcels sent to auction)
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Sequence

import numpy as np


def smooth(values: Sequence[float], window: int = 50) -> np.ndarray:
    """Apply sliding-window mean smoothing.

    Args:
        values: Raw signal.
        window: Smoothing window size.

    Returns:
        Smoothed array of same length (uses partial windows at edges).
    """
    arr = np.array(values, dtype=np.float64)
    if len(arr) <= 1:
        return arr
    kernel = np.ones(min(window, len(arr))) / min(window, len(arr))
    # Use 'same' mode with zero-padding, then correct edges
    smoothed = np.convolve(arr, kernel, mode="same")
    # Fix edge effects by recomputing with actual window
    result = np.empty_like(arr)
    for i in range(len(arr)):
        lo = max(0, i - window // 2)
        hi = min(len(arr), i + window // 2 + 1)
        result[i] = arr[lo:hi].mean()
    return result


def plot_training_curves(
    history: List,
    output_path: str | Path = "outputs/rl_capa_training.png",
    window: int = 50,
) -> Path:
    """Plot all 7 training curves and save to file.

    Args:
        history: List of EpisodeLog from trainer.
        output_path: Destination image path.
        window: Sliding window size for smoothing.

    Returns:
        Path to saved image.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    episodes = [h.episode for h in history]
    rewards = [h.total_reward for h in history]
    loss_v1 = [h.loss_v1 for h in history]
    loss_v2 = [h.loss_v2 for h in history]
    loss_pi1 = [h.loss_pi1 for h in history]
    loss_pi2 = [h.loss_pi2 for h in history]
    mean_batch = [
        float(np.mean(h.batch_sizes)) if h.batch_sizes else 0.0
        for h in history
    ]
    cross_rates = [h.cross_rate for h in history]

    fig, axes = plt.subplots(4, 2, figsize=(14, 16))
    fig.suptitle("RL-CAPA Training Curves", fontsize=14, fontweight="bold")

    curves = [
        (axes[0, 0], rewards, "Episode Reward", "Reward"),
        (axes[0, 1], loss_v1, "Critic 1 Loss (L_V1)", "Loss"),
        (axes[1, 0], loss_v2, "Critic 2 Loss (L_V2)", "Loss"),
        (axes[1, 1], loss_pi1, "Policy Loss π1", "Loss"),
        (axes[2, 0], loss_pi2, "Policy Loss π2", "Loss"),
        (axes[2, 1], mean_batch, "Mean Batch Size", "Seconds"),
        (axes[3, 0], cross_rates, "Cross Rate", "Rate"),
    ]

    for ax, data, title, ylabel in curves:
        raw = np.array(data)
        smoothed = smooth(data, window=window)
        ax.plot(episodes, raw, alpha=0.3, color="tab:blue", linewidth=0.5)
        ax.plot(episodes, smoothed, color="tab:blue", linewidth=1.5)
        ax.set_title(title)
        ax.set_xlabel("Episode")
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.3)

    # Hide unused subplot
    axes[3, 1].set_visible(False)

    plt.tight_layout()
    fig.savefig(str(output_path), dpi=150)
    plt.close(fig)
    return output_path
