"""Utility helpers shared by RL-CAPA training and evaluation."""

from __future__ import annotations

from typing import Iterable, List

import torch


def select_torch_device(requested: str | None = None) -> torch.device:
    """Select the execution device for actor-critic training and evaluation.

    Args:
        requested: Optional explicit device string. When omitted, CUDA is used
            if available; otherwise CPU is selected.

    Returns:
        Resolved torch device.
    """

    if requested is not None:
        return torch.device(requested)
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def compute_discounted_returns(rewards: Iterable[float], discount_factor: float) -> List[float]:
    """Compute Monte-Carlo discounted returns from the end of one episode.

    Args:
        rewards: Step rewards ordered from the beginning of the episode.
        discount_factor: Gamma used for backward discounted accumulation.

    Returns:
        Discounted return for every step in the same order.
    """

    reward_values = list(rewards)
    discounted: List[float] = [0.0 for _ in reward_values]
    running = 0.0
    for index in reversed(range(len(discounted))):
        reward = reward_values[index]
        running = reward + discount_factor * running
        discounted[index] = running
    return discounted
