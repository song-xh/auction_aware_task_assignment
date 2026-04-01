"""Shared-environment seeding and cloning helpers for experiment comparisons."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from env.chengdu import ChengduEnvironment


@dataclass(frozen=True)
class ChengduEnvironmentSeed:
    """Store the immutable initialization state needed to replay a Chengdu run.

    Args:
        tasks: Deep-copiable initial task objects.
        local_couriers: Deep-copiable initial local courier objects.
        partner_couriers_by_platform: Deep-copiable initial partner courier pools.
        station_set: Deep-copiable initial station objects.
        travel_model: Shared read-only travel model object.
        platform_base_prices: Platform base-price configuration.
        platform_sharing_rates: Platform sharing-rate configuration.
        platform_qualities: Platform quality configuration.
        movement_callback: Optional legacy movement callback reused across clones.
    """

    tasks: Sequence[Any]
    local_couriers: Sequence[Any]
    partner_couriers_by_platform: Mapping[str, Sequence[Any]]
    station_set: Sequence[Any]
    travel_model: Any
    platform_base_prices: Mapping[str, float]
    platform_sharing_rates: Mapping[str, float]
    platform_qualities: Mapping[str, float]
    movement_callback: Any | None = None


def build_environment_seed(environment: ChengduEnvironment) -> ChengduEnvironmentSeed:
    """Capture a reusable immutable seed from a prepared Chengdu environment."""
    return ChengduEnvironmentSeed(
        tasks=deepcopy(list(environment.tasks)),
        local_couriers=deepcopy(list(environment.local_couriers)),
        partner_couriers_by_platform=deepcopy(
            {
                platform_id: list(couriers)
                for platform_id, couriers in environment.partner_couriers_by_platform.items()
            }
        ),
        station_set=deepcopy(list(environment.station_set)),
        travel_model=environment.travel_model,
        platform_base_prices=dict(environment.platform_base_prices),
        platform_sharing_rates=dict(environment.platform_sharing_rates),
        platform_qualities=dict(environment.platform_qualities),
        movement_callback=environment.movement_callback,
    )


def clone_environment_from_seed(seed: ChengduEnvironmentSeed) -> ChengduEnvironment:
    """Create a fresh mutable Chengdu environment clone from a captured seed."""
    return ChengduEnvironment(
        tasks=deepcopy(list(seed.tasks)),
        local_couriers=deepcopy(list(seed.local_couriers)),
        partner_couriers_by_platform=deepcopy(
            {
                platform_id: list(couriers)
                for platform_id, couriers in seed.partner_couriers_by_platform.items()
            }
        ),
        station_set=deepcopy(list(seed.station_set)),
        travel_model=seed.travel_model,
        platform_base_prices=dict(seed.platform_base_prices),
        platform_sharing_rates=dict(seed.platform_sharing_rates),
        platform_qualities=dict(seed.platform_qualities),
        movement_callback=seed.movement_callback,
    )
