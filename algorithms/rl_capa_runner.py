"""Explicit rl-capa placeholder runner for the unified algorithm registry."""

from __future__ import annotations

from .base import UnavailableAlgorithmRunner


def build_rl_capa_runner() -> UnavailableAlgorithmRunner:
    """Build the explicit rl-capa placeholder without any fallback behavior."""
    return UnavailableAlgorithmRunner(
        algorithm_name="rl-capa",
        reason="the RL environment and DDQN stack are still pending implementation",
    )
