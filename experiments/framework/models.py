"""Typed experiment-framework models shared by point, split, and managed runners."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class ExperimentPointSpec:
    """Describe one seeded comparison point inside a larger experiment suite.

    Args:
        axis_name: Sweep axis name such as ``num_parcels``.
        axis_value: Sweep point value on the chosen axis.
        output_dir: Directory receiving point-level outputs.
        algorithms: Ordered algorithms executed at this point.
        batch_size: Shared batch size in seconds for batch-based runners.
        runner_overrides_by_algorithm: Optional algorithm-specific runner kwargs.
    """

    axis_name: str
    axis_value: int
    output_dir: Path
    algorithms: Sequence[str]
    batch_size: int
    runner_overrides_by_algorithm: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)


@dataclass(frozen=True)
class ExperimentSplitSpec:
    """Describe one split-process seeded comparison experiment.

    Args:
        axis_name: Sweep axis name.
        axis_values: Ordered sweep values.
        tmp_root: Temporary directory for process logs and point outputs.
        output_dir: Final aggregate output directory.
        algorithms: Algorithms run at every point.
        batch_size: Shared batch size in seconds.
        poll_seconds: Launcher polling interval.
        progress_mode: Terminal rendering mode.
        runner_overrides_by_algorithm: Optional algorithm-specific runner kwargs.
    """

    axis_name: str
    axis_values: Sequence[int]
    tmp_root: Path
    output_dir: Path
    algorithms: Sequence[str]
    batch_size: int
    poll_seconds: int
    progress_mode: str = "overwrite"
    runner_overrides_by_algorithm: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)


@dataclass(frozen=True)
class ManagedRoundSpec:
    """Describe one managed experiment round.

    Args:
        name: Stable round identifier.
        rationale: Human-readable reason for running the round.
        runner_overrides_by_algorithm: Per-algorithm override set for this round.
    """

    name: str
    rationale: str
    runner_overrides_by_algorithm: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
