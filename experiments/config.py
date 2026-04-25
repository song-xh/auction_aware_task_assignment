"""Configuration dataclasses for unified experiment orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from capa.config import (
    DEFAULT_CAPA_BATCH_SIZE,
    DEFAULT_COURIER_ALPHA,
    DEFAULT_COURIER_SERVICE_SCORE,
    DEFAULT_IMPGTA_WINDOW_SECONDS,
    DEFAULT_PLATFORM_QUALITY_START,
    DEFAULT_PLATFORM_QUALITY_STEP,
    validate_courier_preference,
)

SUPPORTED_SWEEP_AXES = frozenset({
    "num_parcels",
    "local_couriers",
    "service_radius",
    "platforms",
    "batch_size",
    "courier_capacity",
    "courier_alpha",
})


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
        courier_alpha: Courier detour-preference weight.
        courier_beta: Optional courier service-score weight. When omitted,
            it is derived as `1 - courier_alpha`.
        courier_service_score: Courier service-score proxy used by CAPA/DAPA.
        platform_quality_start: Initial cooperating-platform quality proxy.
        platform_quality_step: Per-platform quality decrement.
        extra: Additional explicitly named parameters such as service radius.
    """

    data_dir: Path
    num_parcels: int = 100
    local_couriers: int = 10
    platforms: int = 2
    couriers_per_platform: int = 5
    batch_size: int = DEFAULT_CAPA_BATCH_SIZE
    prediction_window_seconds: int = DEFAULT_IMPGTA_WINDOW_SECONDS
    prediction_success_rate: float = 0.8
    prediction_sampling_seed: int = 1
    service_radius_km: float | None = None
    courier_capacity: float | None = None
    task_window_start_seconds: float | None = None
    task_window_end_seconds: float | None = None
    task_sampling_seed: int = 1
    courier_alpha: float = DEFAULT_COURIER_ALPHA
    courier_beta: float | None = None
    courier_service_score: float = DEFAULT_COURIER_SERVICE_SCORE
    platform_quality_start: float = DEFAULT_PLATFORM_QUALITY_START
    platform_quality_step: float = DEFAULT_PLATFORM_QUALITY_STEP
    rl_min_batch_size: int = 10
    rl_max_batch_size: int = 20
    rl_step_seconds: int = 60
    rl_num_episodes: int = 500
    rl_lr_actor: float = 0.001
    rl_lr_critic: float = 0.001
    rl_discount_factor: float = 0.9
    rl_entropy_coeff: float = 0.01
    rl_max_grad_norm: float = 0.5
    rl_device: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate and materialize derived courier preference weights."""

        alpha, beta = validate_courier_preference(self.courier_alpha, self.courier_beta)
        object.__setattr__(self, "courier_alpha", alpha)
        object.__setattr__(self, "courier_beta", beta)

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
            "prediction_success_rate": self.prediction_success_rate,
            "prediction_sampling_seed": self.prediction_sampling_seed,
            "service_radius_km": self.service_radius_km,
            "courier_capacity": self.courier_capacity,
            "task_window_start_seconds": self.task_window_start_seconds,
            "task_window_end_seconds": self.task_window_end_seconds,
            "task_sampling_seed": self.task_sampling_seed,
            "courier_alpha": self.courier_alpha,
            "courier_beta": self.courier_beta,
            "courier_service_score": self.courier_service_score,
            "platform_quality_start": self.platform_quality_start,
            "platform_quality_step": self.platform_quality_step,
            "rl_min_batch_size": self.rl_min_batch_size,
            "rl_max_batch_size": self.rl_max_batch_size,
            "rl_step_seconds": self.rl_step_seconds,
            "rl_num_episodes": self.rl_num_episodes,
            "rl_lr_actor": self.rl_lr_actor,
            "rl_lr_critic": self.rl_lr_critic,
            "rl_discount_factor": self.rl_discount_factor,
            "rl_entropy_coeff": self.rl_entropy_coeff,
            "rl_max_grad_norm": self.rl_max_grad_norm,
            "rl_device": self.rl_device,
            "extra": dict(self.extra),
        }
        for key, value in kwargs.items():
            if key == "extra":
                values["extra"] = dict(value)
            else:
                values[key] = value
        if "courier_alpha" in kwargs and "courier_beta" not in kwargs:
            values["courier_beta"] = None
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
        if self.service_radius_km is not None:
            kwargs["service_radius_km"] = self.service_radius_km
        if self.courier_capacity is not None:
            kwargs["courier_capacity"] = self.courier_capacity
        if self.task_window_start_seconds is not None:
            kwargs["task_window_start_seconds"] = self.task_window_start_seconds
        if self.task_window_end_seconds is not None:
            kwargs["task_window_end_seconds"] = self.task_window_end_seconds
        kwargs["task_sampling_seed"] = self.task_sampling_seed
        kwargs["courier_alpha"] = self.courier_alpha
        kwargs["courier_beta"] = self.courier_beta
        kwargs["courier_service_score"] = self.courier_service_score
        kwargs["platform_quality_start"] = self.platform_quality_start
        kwargs["platform_quality_step"] = self.platform_quality_step
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
    values: tuple[int | float, ...]
    base: ExperimentConfig


def apply_sweep_axis(config: ExperimentConfig, axis: str, value: int | float) -> ExperimentConfig:
    """Apply one supported sweep axis update to an experiment configuration.

    Args:
        config: Base experiment configuration.
        axis: Sweep axis name.
        value: New value for the chosen axis.

    Returns:
        A new configuration with the selected axis updated.

    Raises:
        ValueError: The axis name is unknown to the experiment layer.
    """
    if axis not in SUPPORTED_SWEEP_AXES:
        raise ValueError(f"Unsupported sweep axis `{axis}`.")
    if axis == "service_radius":
        return config.with_update(service_radius_km=float(value))
    if axis == "courier_capacity":
        return config.with_update(courier_capacity=float(value))
    if axis == "courier_alpha":
        return config.with_update(courier_alpha=float(value), courier_beta=None)
    if axis in {"num_parcels", "local_couriers", "platforms", "batch_size"}:
        return config.with_update(**{axis: int(value)})
    raise ValueError(f"Unsupported sweep axis `{axis}`.")
