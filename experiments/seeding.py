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
    service_radius_km: float | None = None


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
        service_radius_km=environment.service_radius_km,
    )


def clone_environment_from_seed(seed: ChengduEnvironmentSeed) -> ChengduEnvironment:
    """Create a fresh mutable Chengdu environment clone from a captured seed."""
    environment = ChengduEnvironment(
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
        service_radius_km=seed.service_radius_km,
    )
    _rebind_courier_station_references(environment)
    _rebind_station_member_references(environment)
    return environment


def _rebind_courier_station_references(environment: ChengduEnvironment) -> None:
    """Reconnect cloned courier station references back to the cloned station set."""
    station_lookup = _build_station_lookup(environment.station_set)
    for courier in list(environment.local_couriers):
        _rebind_single_courier_station(courier, station_lookup)
    for couriers in environment.partner_couriers_by_platform.values():
        for courier in couriers:
            _rebind_single_courier_station(courier, station_lookup)


def _build_station_lookup(stations: Sequence[Any]) -> dict[Any, Any]:
    """Index cloned stations by their stable identifiers."""
    lookup: dict[Any, Any] = {}
    for station in stations:
        if isinstance(station, dict):
            if "station_id" in station:
                lookup[station["station_id"]] = station
            if "num" in station:
                lookup[station["num"]] = station
        else:
            if hasattr(station, "num"):
                lookup[getattr(station, "num")] = station
            if hasattr(station, "station_id"):
                lookup[getattr(station, "station_id")] = station
    return lookup


def _rebind_single_courier_station(courier: Any, station_lookup: dict[Any, Any]) -> None:
    """Point one courier's station reference at the station clone held by the environment."""
    if isinstance(courier, dict):
        station_key = courier.get("station_num")
        if station_key in station_lookup:
            courier["station"] = station_lookup[station_key]
        return
    station_key = getattr(courier, "station_num", None)
    if station_key in station_lookup:
        courier.station = station_lookup[station_key]


def _rebind_station_member_references(environment: ChengduEnvironment) -> None:
    """Reconnect cloned station task and courier buffers to the cloned environment objects."""
    courier_lookup = _build_object_lookup(
        [*environment.local_couriers, *[courier for couriers in environment.partner_couriers_by_platform.values() for courier in couriers]]
    )
    task_lookup = _build_object_lookup(environment.tasks)
    for station in environment.station_set:
        _rebind_station_sequence(station, "courier_set", courier_lookup)
        _rebind_station_sequence(station, "f_pick_task_set", task_lookup)
        _rebind_station_sequence(station, "station_task_set", task_lookup)


def _build_object_lookup(objects: Sequence[Any]) -> dict[str, Any]:
    """Index cloned legacy objects by their stable identifiers when available."""
    lookup: dict[str, Any] = {}
    for obj in objects:
        object_id = _stable_object_id(obj)
        if object_id is not None:
            lookup[object_id] = obj
    return lookup


def _stable_object_id(obj: Any) -> str | None:
    """Extract a stable identifier used to reconnect deep-copied legacy references."""
    if isinstance(obj, dict):
        for key in ("num", "task_id", "courier_id", "station_id"):
            if key in obj:
                return str(obj[key])
        return None
    for attribute in ("num", "task_id", "courier_id", "station_id"):
        if hasattr(obj, attribute):
            return str(getattr(obj, attribute))
    return None


def _rebind_station_sequence(station: Any, attribute: str, lookup: dict[str, Any]) -> None:
    """Replace one station-owned legacy sequence with the matching cloned objects."""
    if isinstance(station, dict):
        sequence = station.get(attribute)
    else:
        sequence = getattr(station, attribute, None)
    if sequence is None:
        return
    rebound: list[Any] = []
    for item in list(sequence):
        object_id = _stable_object_id(item)
        if object_id is not None and object_id in lookup:
            rebound.append(lookup[object_id])
    if isinstance(station, dict):
        station[attribute] = rebound
    else:
        setattr(station, attribute, rebound)
