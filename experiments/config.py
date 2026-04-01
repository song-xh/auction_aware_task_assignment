"""Configuration dataclasses for unified experiment orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SUPPORTED_SWEEP_AXES = frozenset({"num_parcels", "local_couriers", "platforms", "batch_size"})
UNSUPPORTED_PAPER_AXES = frozenset({"service_radius"})


@dataclass(frozen=True)
class ExperimentConfig:
    """Define the common configuration required to build a Chengdu experiment point.

    Args:
        data_dir: Repository data directory containing Chengdu inputs.
        num_parcels: Number of parcels included in the run.
        local_couriers: Number of local couriers.
        platforms: Number of cooperating platforms.
        couriers_per_platform: Number of couriers per cooperating platform.
        batch_size: Batch window size in seconds.
        prediction_window_seconds: Future observation window for ImpGTA-style baselines.
        extra: Additional explicitly named parameters such as service radius.
    """

    data_dir: Path
    num_parcels: int = 100
    local_couriers: int = 10
    platforms: int = 2
    couriers_per_platform: int = 5
    batch_size: int = 300
    prediction_window_seconds: int = 180
    extra: dict[str, Any] = field(default_factory=dict)

    def with_update(self, **kwargs: Any) -> "ExperimentConfig":
        """Return a new config with explicit field updates applied."""
        values = {
            "data_dir": self.data_dir,
            "num_parcels": self.num_parcels,
            "local_couriers": self.local_couriers,
            "platforms": self.platforms,
            "couriers_per_platform": self.couriers_per_platform,
            "batch_size": self.batch_size,
            "prediction_window_seconds": self.prediction_window_seconds,
            "extra": dict(self.extra),
        }
        for key, value in kwargs.items():
            if key == "extra":
                values["extra"] = dict(value)
            else:
                values[key] = value
        return ExperimentConfig(**values)

    def as_environment_kwargs(self) -> dict[str, Any]:
        """Translate this config into Chengdu environment build keyword arguments."""
        kwargs = {
            "data_dir": self.data_dir,
            "num_parcels": self.num_parcels,
            "local_courier_count": self.local_couriers,
            "cooperating_platform_count": self.platforms,
            "couriers_per_platform": self.couriers_per_platform,
        }
        kwargs.update(self.extra)
        return kwargs


@dataclass(frozen=True)
class SweepConfig:
    """Define a one-dimensional sweep over a base experiment configuration.

    Args:
        axis: Name of the varying parameter.
        values: Values explored on that axis.
        base: Fixed experiment configuration shared across the sweep.
    """

    axis: str
    values: tuple[int, ...]
    base: ExperimentConfig


def apply_sweep_axis(config: ExperimentConfig, axis: str, value: int) -> ExperimentConfig:
    """Apply one supported sweep axis update to an experiment configuration.

    Args:
        config: Base experiment configuration.
        axis: Sweep axis name.
        value: New value for the chosen axis.

    Returns:
        A new configuration with the selected axis updated.

    Raises:
        NotImplementedError: The axis is paper-relevant but not yet exposed by the environment.
        ValueError: The axis name is unknown to the experiment layer.
    """

    if axis in UNSUPPORTED_PAPER_AXES:
        raise NotImplementedError(f"The sweep axis `{axis}` is not exposed by the unified Chengdu environment yet.")
    if axis not in SUPPORTED_SWEEP_AXES:
        raise ValueError(f"Unsupported sweep axis `{axis}`.")
    return config.with_update(**{axis: value})
