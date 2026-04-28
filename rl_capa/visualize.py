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

import os
from pathlib import Path
from typing import List, Sequence

import numpy as np

from capa.metrics import compute_completion_rate, compute_total_revenue
from capa.models import BatchReport


def _configure_matplotlib_cache() -> None:
    """Ensure matplotlib uses a writable cache directory in this environment."""

    cache_dir = Path("/tmp/matplotlib")
    cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(cache_dir))


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
    _configure_matplotlib_cache()
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
    mean_batch = [h.mean_batch_size for h in history]
    cross_rates = [h.cross_rate for h in history]
    entropy_pi1 = [h.entropy_pi1 for h in history]
    entropy_pi2 = [h.entropy_pi2 for h in history]

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
        (axes[3, 1], entropy_pi2, "Policy Entropy π2", "Entropy"),
    ]

    for ax, data, title, ylabel in curves:
        raw = np.array(data)
        smoothed = smooth(data, window=window)
        ax.plot(episodes, raw, alpha=0.45, color="tab:blue", linewidth=0.6, label="raw")
        ax.plot(episodes, smoothed, color="tab:blue", linewidth=1.5)
        ax.set_title(title)
        ax.set_xlabel("Episode")
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.3)

    axes[3, 1].plot(
        episodes,
        smooth(entropy_pi1, window=window),
        color="tab:orange",
        linewidth=1.2,
        label="π1 smoothed",
    )
    axes[3, 1].legend(loc="best", fontsize=8)

    plt.tight_layout()
    fig.savefig(str(output_path), dpi=150)
    plt.close(fig)
    return output_path


def plot_evaluation_curves(
    batch_reports: Sequence[BatchReport],
    total_parcels: int,
    total_revenue: float,
    completion_rate: float,
    batch_processing_time: float,
    output_dir: str | Path,
) -> dict[str, str]:
    """Plot batch-level evaluation curves and return their saved paths.

    Args:
        batch_reports: Realized batch reports from one evaluation episode.
        total_parcels: Total parcel count in the episode.
        total_revenue: Final TR metric used in the chart title.
        completion_rate: Final CR metric used in the chart title.
        batch_processing_time: Final BPT metric used in the chart title.
        output_dir: Directory receiving the saved plot files.

    Returns:
        Mapping of metric label to saved image path.
    """
    _configure_matplotlib_cache()
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    normalized_output_dir = Path(output_dir)
    normalized_output_dir.mkdir(parents=True, exist_ok=True)

    tr_values: list[float] = []
    cr_values: list[float] = []
    bpt_values: list[float] = []
    batch_indices = list(range(1, len(batch_reports) + 1))

    for report in batch_reports:
        assignments = [*report.local_assignments, *report.cross_assignments]
        tr_values.append(compute_total_revenue(assignments))
        cr_values.append(
            compute_completion_rate(
                [None] * report.delivered_parcel_count,
                total_parcels,
            )
        )
        bpt_values.append(report.timing.decision_time_seconds)

    paths = {
        "TR": str(normalized_output_dir / "tr_over_batches.png"),
        "CR": str(normalized_output_dir / "cr_over_batches.png"),
        "BPT": str(normalized_output_dir / "bpt_over_batches.png"),
    }

    plt.figure()
    plt.plot(batch_indices, tr_values, marker="o")
    plt.title(f"TR Over Batches (Total={total_revenue:.2f})")
    plt.xlabel("Batch")
    plt.ylabel("TR")
    plt.tight_layout()
    plt.savefig(paths["TR"], dpi=150)
    plt.close()

    plt.figure()
    plt.plot(batch_indices, cr_values, marker="o")
    plt.title(f"CR Over Batches (Final={completion_rate:.4f})")
    plt.xlabel("Batch")
    plt.ylabel("CR")
    plt.tight_layout()
    plt.savefig(paths["CR"], dpi=150)
    plt.close()

    plt.figure()
    plt.plot(batch_indices, bpt_values, marker="o")
    plt.title(f"BPT Over Batches (Total={batch_processing_time:.4f}s)")
    plt.xlabel("Batch")
    plt.ylabel("BPT (s)")
    plt.tight_layout()
    plt.savefig(paths["BPT"], dpi=150)
    plt.close()

    return paths
