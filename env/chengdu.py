"""Reusable adapters and runners for the legacy Chengdu simulation environment."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from time import perf_counter
from typing import Any, Callable, Dict, Iterable, List, Mapping, MutableSequence, Sequence

from capa.batch_distance import BatchDistanceMatrix, PersistentDirectedDistanceCache
from capa.cache import InsertionCache
from capa.cama import run_cama
from capa.dapa import run_dapa
from capa.geo import GeoIndex
from capa.metrics import build_run_metrics
from capa.models import Assignment, BatchReport, CAPAConfig, CAPAResult, CooperatingPlatform, Courier, Parcel
from capa.timing import TimingAccumulator, TimedTravelModel
from capa.utility import find_best_local_insertion


@dataclass(frozen=True)
class StationBlueprint:
    """Store the immutable geometry needed to recreate a legacy station quickly."""

    num: int
    l_lng: float
    l_lat: float
    l_node: Any
    station_range: tuple[float, float, float, float]


@dataclass
class ChengduEnvironment:
    """Store the reusable Chengdu simulation state shared by all Chengdu algorithms."""

    tasks: Sequence[Any]
    local_couriers: Sequence[Any]
    partner_couriers_by_platform: Mapping[str, Sequence[Any]]
    station_set: Sequence[Any]
    travel_model: Any
    platform_base_prices: Mapping[str, float]
    platform_sharing_rates: Mapping[str, float]
    platform_qualities: Mapping[str, float]
    movement_callback: Callable[[MutableSequence[Any], MutableSequence[Any], int, Sequence[Any]], None] | None = None
    service_radius_km: float | None = None
    courier_capacity: float | None = None
    geo_index: GeoIndex | None = None
    travel_speed_m_per_s: float = 0.0

    @classmethod
    def build(
        cls,
        data_dir: Any,
        num_parcels: int,
        local_courier_count: int,
        cooperating_platform_count: int,
        couriers_per_platform: int,
        service_radius_km: float | None = None,
        courier_capacity: float | None = None,
    ) -> "ChengduEnvironment":
        """Build a Chengdu environment from the legacy framework inputs."""
        return build_framework_chengdu_environment(
            data_dir=data_dir,
            num_parcels=num_parcels,
            local_courier_count=local_courier_count,
            cooperating_platform_count=cooperating_platform_count,
            couriers_per_platform=couriers_per_platform,
            service_radius_km=service_radius_km,
            courier_capacity=courier_capacity,
        )

    def all_partner_couriers(self) -> list[Any]:
        """Flatten all partner couriers while preserving platform grouping on the object itself."""
        return [courier for couriers in self.partner_couriers_by_platform.values() for courier in couriers]

    def all_couriers(self) -> list[Any]:
        """Return every active courier in the environment."""
        return [*self.local_couriers, *self.all_partner_couriers()]

    def snapshot_for_algorithm(self) -> dict[str, Any]:
        """Return the current environment state in a stable algorithm-facing dictionary."""
        return {
            "tasks": list(self.tasks),
            "local_couriers": list(self.local_couriers),
            "partner_couriers_by_platform": {
                platform_id: list(couriers)
                for platform_id, couriers in self.partner_couriers_by_platform.items()
            },
            "station_set": list(self.station_set),
            "travel_model": self.travel_model,
            "platform_base_prices": dict(self.platform_base_prices),
            "platform_sharing_rates": dict(self.platform_sharing_rates),
            "platform_qualities": dict(self.platform_qualities),
            "service_radius_km": self.service_radius_km,
            "courier_capacity": self.courier_capacity,
            "geo_index": self.geo_index,
            "travel_speed_m_per_s": self.travel_speed_m_per_s,
        }

    def advance(self, seconds: int) -> None:
        """Advance the environment through the underlying movement callback."""
        if seconds <= 0:
            return
        movement = self.movement_callback or framework_movement_callback
        movement(
            list(self.local_couriers),
            flatten_partner_couriers(self.partner_couriers_by_platform),
            seconds,
            self.station_set,
        )

    def drain(self, step_seconds: int = 60) -> int:
        """Advance the environment until all active legacy routes are empty."""
        movement = self.movement_callback or framework_movement_callback
        return drain_legacy_routes(
            local_couriers=list(self.local_couriers),
            partner_couriers_by_platform={
                platform_id: list(couriers)
                for platform_id, couriers in self.partner_couriers_by_platform.items()
            },
            station_set=self.station_set,
            step_seconds=step_seconds,
            movement_callback=movement,
        )

    def apply_assignments(self, assignments: Sequence[tuple[Any, Any, int]]) -> None:
        """Write a sequence of accepted legacy assignments back into courier routes."""
        for task, courier, insertion_index in assignments:
            apply_assignment_to_legacy_courier(task, courier, insertion_index)


LegacyChengduEnvironment = ChengduEnvironment


def limit_legacy_tasks(
    pick_tasks: Sequence[Any],
    delivery_tasks: Sequence[Any],
    num_parcels: int,
    required_couriers: int,
) -> tuple[list[Any], list[Any]]:
    """Trim legacy pick-up and delivery inputs to the volume required by the requested run."""
    if num_parcels <= 0:
        raise ValueError("The requested parcel count must be positive.")
    if required_couriers <= 0:
        raise ValueError("The requested courier count must be positive.")
    ordered_pick = sort_legacy_tasks(pick_tasks)
    ordered_delivery = sort_legacy_tasks(delivery_tasks)
    limited_pick = ordered_pick[:num_parcels]
    limited_delivery = ordered_delivery[:required_couriers]
    if len(limited_pick) < num_parcels:
        raise ValueError(f"Only {len(limited_pick)} pick-up tasks are available, fewer than the requested {num_parcels}.")
    if len(limited_delivery) < required_couriers:
        raise ValueError(
            f"Only {len(limited_delivery)} delivery tasks are available, fewer than the required {required_couriers} courier seeds."
        )
    return limited_pick, limited_delivery


def iter_delivery_seed_counts(required_couriers: int, total_delivery_tasks: int) -> Iterable[int]:
    """Yield progressively larger delivery-task budgets until the full dataset is exhausted."""
    if required_couriers <= 0:
        raise ValueError("The requested courier count must be positive.")
    if total_delivery_tasks <= 0:
        raise ValueError("At least one delivery task is required.")
    current = min(required_couriers, total_delivery_tasks)
    while True:
        yield current
        if current >= total_delivery_tasks:
            break
        current = min(total_delivery_tasks, current * 2)


def sort_legacy_tasks(tasks: Sequence[Any]) -> list[Any]:
    """Return legacy tasks sorted by request time, deadline, and identifier."""
    return sorted(
        tasks,
        key=lambda item: (float(getattr(item, "s_time")), float(getattr(item, "d_time")), str(getattr(item, "num"))),
    )


def select_station_pick_tasks(station_set: Sequence[Any], ordered_pick_tasks: Sequence[Any], num_parcels: int) -> list[Any]:
    """Assign pick-up tasks to legacy stations using the original rectangular station ranges."""
    if num_parcels <= 0:
        raise ValueError("The requested parcel count must be positive.")
    for station in station_set:
        station.f_pick_task_set = []
    selected: list[Any] = []
    for task in ordered_pick_tasks:
        for station in station_set:
            station_range = getattr(station, "station_range", None)
            if not station_range or len(station_range) != 4:
                continue
            if station_range[0] <= float(getattr(task, "l_lng")) < station_range[1] and station_range[2] <= float(getattr(task, "l_lat")) < station_range[3]:
                station.f_pick_task_set.append(task)
                selected.append(task)
                break
        if len(selected) >= num_parcels:
            break
    return selected


def assign_delivery_tasks_to_stations(station_set: Sequence[Any], ordered_delivery_tasks: Sequence[Any]) -> None:
    """Assign delivery tasks to stations using the original rectangular station ranges."""
    for station in station_set:
        station.station_task_set = []
    for task in ordered_delivery_tasks:
        for station in station_set:
            station_range = getattr(station, "station_range", None)
            if not station_range or len(station_range) != 4:
                continue
            if station_range[0] <= float(getattr(task, "l_lng")) < station_range[1] and station_range[2] <= float(getattr(task, "l_lat")) < station_range[3]:
                station.station_task_set.append(task)
                break


@lru_cache(maxsize=8)
def load_station_blueprints(data_dir_str: str, parts_num: int) -> tuple[StationBlueprint, ...]:
    """Cache the immutable station geometry derived from the legacy Chengdu map."""
    import Framework_ChengDu as framework

    data_dir = Path(data_dir_str)
    generator = framework.GenerateStation(str(data_dir / "map_ChengDu"), str(data_dir / "order_20161101_deal"), parts_num)
    range_lng, range_lat = generator.edge_station()
    blueprints: list[StationBlueprint] = []
    count = 0
    for i in range(parts_num - 1):
        for j in range(parts_num - 1):
            count += 1
            l_lng = (range_lng[i] + range_lng[i + 1]) / 2
            l_lat = (range_lat[j] + range_lat[j + 1]) / 2
            l_node = framework.g.findNode(l_lng, l_lat, framework.s)
            blueprints.append(
                StationBlueprint(
                    num=count,
                    l_lng=l_lng,
                    l_lat=l_lat,
                    l_node=l_node,
                    station_range=(range_lng[i], range_lng[i + 1], range_lat[j], range_lat[j + 1]),
                )
            )
    return tuple(blueprints)


def instantiate_stations_from_blueprints(framework: Any, blueprints: Sequence[StationBlueprint]) -> list[Any]:
    """Create fresh legacy station objects from cached geometry blueprints."""
    stations = [
        framework.Station(
            blueprint.num,
            blueprint.l_lng,
            blueprint.l_lat,
            blueprint.l_node,
            list(blueprint.station_range),
        )
        for blueprint in blueprints
    ]
    return stations


def generate_origin_schedule_with_retry(
    framework: Any,
    station_set: Sequence[Any],
    required_couriers: int,
    candidate_seed_count: int,
    preference: float,
) -> list[Any]:
    """Retry legacy courier seeding when the requested sample exceeds the true generated population."""
    requested_couriers = min(required_couriers, candidate_seed_count)
    while requested_couriers > 0:
        framework.parameter_courier_num = requested_couriers
        try:
            return framework.GenerateOriginSchedule(station_set, preference)
        except ValueError as error:
            if "Sample larger than population" not in str(error):
                raise
            requested_couriers -= 1
    return []


def legacy_task_to_parcel(task: Any) -> Parcel:
    """Convert a legacy Chengdu task object into the CAPA parcel model."""
    return Parcel(
        parcel_id=str(getattr(task, "num")),
        location=getattr(task, "l_node"),
        arrival_time=int(float(getattr(task, "s_time"))),
        deadline=int(float(getattr(task, "d_time"))),
        weight=float(getattr(task, "weight")),
        fare=float(getattr(task, "fare")),
    )


def ensure_legacy_courier_station(courier: Any, station_by_num: Mapping[int, Any]) -> None:
    """Attach the full station object to a legacy courier when only `station_num` is present."""
    if getattr(courier, "station", None) is None:
        station_num = getattr(courier, "station_num", None)
        if station_num not in station_by_num:
            raise ValueError(f"Legacy courier {getattr(courier, 'num', courier)!r} is missing a valid station mapping.")
        courier.station = station_by_num[station_num]


def legacy_courier_to_capa(courier: Any, courier_id: str) -> Courier:
    """Project a legacy courier into the CAPA courier state expected by CAMA and DAPA."""
    station = getattr(courier, "station", None)
    if station is None:
        raise ValueError("Legacy courier must expose a `station` object before conversion.")
    return Courier(
        courier_id=courier_id,
        current_location=getattr(courier, "location"),
        depot_location=getattr(station, "l_node"),
        capacity=float(getattr(courier, "max_weight")),
        current_load=float(getattr(courier, "re_weight")),
        route_locations=[getattr(task, "l_node") for task in getattr(courier, "re_schedule", [])],
        available_from=0,
        alpha=float(getattr(courier, "w", 0.4)),
        beta=float(getattr(courier, "c", 0.6)),
        service_score=float(getattr(courier, "service_score", 0.8)),
    )


def local_courier_snapshot_id(courier: Any) -> str:
    """Return the stable CAPA snapshot identifier for one local legacy courier."""

    return f"local-{getattr(courier, 'num')}"


def partner_courier_snapshot_id(platform_id: str, courier: Any) -> str:
    """Return the stable CAPA snapshot identifier for one partner legacy courier."""

    return f"{platform_id}-{getattr(courier, 'num')}"


class LegacyCourierSnapshotCache:
    """Reuse CAPA courier projections while the underlying legacy state is unchanged."""

    def __init__(self) -> None:
        """Initialize the snapshot cache storage."""
        self._entries: dict[str, tuple[tuple[Any, ...], Courier]] = {}

    def get(self, courier: Any, courier_id: str) -> Courier:
        """Return a cached courier snapshot or rebuild it if the legacy state changed.

        Args:
            courier: Legacy courier object.
            courier_id: Stable synthesized courier identifier.

        Returns:
            CAPA courier snapshot reflecting the current legacy state.
        """

        signature = self._build_signature(courier)
        cached = self._entries.get(courier_id)
        if cached is not None and cached[0] == signature:
            return cached[1]
        snapshot = legacy_courier_to_capa(courier, courier_id=courier_id)
        self._entries[courier_id] = (signature, snapshot)
        return snapshot

    def clear(self) -> None:
        """Drop every cached courier projection."""

        self._entries.clear()

    def invalidate(self, courier_id: str) -> None:
        """Drop the cached projection for one courier identifier.

        Args:
            courier_id: Stable synthesized courier identifier.
        """

        self._entries.pop(courier_id, None)

    def _build_signature(self, courier: Any) -> tuple[Any, ...]:
        """Build a stable signature for the legacy courier state used by CAPA."""

        station = getattr(courier, "station", None)
        station_node = None if station is None else getattr(station, "l_node", None)
        return (
            getattr(courier, "location"),
            float(getattr(courier, "re_weight", 0.0)),
            float(getattr(courier, "max_weight")),
            station_node,
            tuple(getattr(task, "l_node") for task in getattr(courier, "re_schedule", [])),
            float(getattr(courier, "w", 0.4)),
            float(getattr(courier, "c", 0.6)),
            float(getattr(courier, "service_score", 0.8)),
        )


def legacy_platform_to_capa(
    platform_id: str,
    couriers: Sequence[Any],
    base_price: float,
    sharing_rate_gamma: float,
    historical_quality: float,
    snapshot_cache: LegacyCourierSnapshotCache | None = None,
) -> CooperatingPlatform:
    """Convert a legacy courier pool into a cooperating platform snapshot for DAPA."""
    return CooperatingPlatform(
        platform_id=platform_id,
        couriers=[
            (
                snapshot_cache.get(courier, courier_id=partner_courier_snapshot_id(platform_id, courier))
                if snapshot_cache is not None
                else legacy_courier_to_capa(courier, courier_id=partner_courier_snapshot_id(platform_id, courier))
            )
            for courier in couriers
        ],
        base_price=base_price,
        sharing_rate_gamma=sharing_rate_gamma,
        historical_quality=historical_quality,
    )


def apply_assignment_to_legacy_courier(task: Any, courier: Any, insertion_index: int) -> None:
    """Write an accepted assignment back into the legacy route buffer and carried-load state."""
    schedule = getattr(courier, "re_schedule")
    if insertion_index < 0 or insertion_index > len(schedule):
        schedule.append(task)
    else:
        schedule.insert(insertion_index, task)
    courier.re_weight = float(getattr(courier, "re_weight")) + float(getattr(task, "weight"))
    courier.batch_take = int(getattr(courier, "batch_take", 0)) + 1


def bind_assignment_to_legacy_objects(assignment: Assignment, task: Any, courier: Any) -> Assignment:
    """Rebuild an assignment record so reports point at the legacy task and courier objects."""
    return Assignment(
        parcel=legacy_task_to_parcel(task),
        courier=assignment.courier,
        mode=assignment.mode,
        platform_id=assignment.platform_id,
        courier_payment=assignment.courier_payment,
        platform_payment=assignment.platform_payment,
        local_platform_revenue=assignment.local_platform_revenue,
        cooperating_platform_revenue=assignment.cooperating_platform_revenue,
        courier_revenue=assignment.courier_revenue,
        utility_value=assignment.utility_value,
    )


def group_legacy_tasks_by_batch(tasks: Sequence[Any], batch_seconds: int) -> List[List[Any]]:
    """Group legacy tasks into fixed-width time batches ordered by request time."""
    if batch_seconds <= 0:
        raise ValueError("Batch duration must be positive.")
    if not tasks:
        return []
    tasks_sorted = sorted(tasks, key=lambda item: (float(getattr(item, "s_time")), float(getattr(item, "d_time")), str(getattr(item, "num"))))
    start_time = float(getattr(tasks_sorted[0], "s_time"))
    buckets: Dict[int, List[Any]] = defaultdict(list)
    for task in tasks_sorted:
        bucket_index = int((float(getattr(task, "s_time")) - start_time) // batch_seconds)
        buckets[bucket_index].append(task)
    return [buckets[index] for index in sorted(buckets)]


def bucketize_legacy_tasks_by_batch(tasks: Sequence[Any], batch_seconds: int) -> tuple[int, Dict[int, List[Any]]]:
    """Index legacy tasks by batch window while preserving empty-window offsets.

    Args:
        tasks: Legacy task sequence.
        batch_seconds: Batch duration in seconds.

    Returns:
        A tuple of `(first_batch_start, bucket_lookup)` where `bucket_lookup`
        maps zero-based batch indices to the tasks arriving in that window.
    """

    if batch_seconds <= 0:
        raise ValueError("Batch duration must be positive.")
    if not tasks:
        return 0, {}
    tasks_sorted = sort_legacy_tasks(tasks)
    first_batch_start = int(float(getattr(tasks_sorted[0], "s_time")))
    bucket_lookup: Dict[int, List[Any]] = defaultdict(list)
    for task in tasks_sorted:
        bucket_index = int((float(getattr(task, "s_time")) - first_batch_start) // batch_seconds)
        bucket_lookup[bucket_index].append(task)
    return first_batch_start, dict(bucket_lookup)


def framework_movement_callback(
    local_couriers: MutableSequence[Any],
    partner_couriers: MutableSequence[Any],
    step_seconds: int,
    station_set: Sequence[Any],
) -> None:
    """Advance legacy couriers along the original Chengdu road-network simulator."""
    import Framework_ChengDu as framework

    for courier in list(local_couriers):
        framework.WalkAlongRoute(courier, step_seconds, courier.location, 0, 0, step_seconds, local_couriers, station_set)
    for courier in list(partner_couriers):
        framework.WalkAlongRoute(courier, step_seconds, courier.location, 0, 0, step_seconds, partner_couriers, station_set)


def flatten_partner_couriers(partner_couriers_by_platform: Mapping[str, Sequence[Any]]) -> list[Any]:
    """Flatten partner couriers from a platform-indexed mapping into one sequence."""
    return [courier for couriers in partner_couriers_by_platform.values() for courier in couriers]


def has_pending_legacy_routes(local_couriers: Sequence[Any], partner_couriers_by_platform: Mapping[str, Sequence[Any]]) -> bool:
    """Return whether any legacy courier still has accepted parcels in its remaining route."""
    for courier in [*local_couriers, *flatten_partner_couriers(partner_couriers_by_platform)]:
        if getattr(courier, "re_schedule", []):
            return True
    return False


def current_legacy_route_task_ids(local_couriers: Sequence[Any], partner_couriers_by_platform: Mapping[str, Sequence[Any]]) -> set[str]:
    """Return the parcel identifiers still riding in any active legacy courier route."""
    route_task_ids: set[str] = set()
    for courier in [*local_couriers, *flatten_partner_couriers(partner_couriers_by_platform)]:
        for task in getattr(courier, "re_schedule", []):
            route_task_ids.add(str(getattr(task, "num")))
    return route_task_ids


def partition_terminal_backlog(
    unresolved_tasks: Sequence[Any],
    now: int,
    active_local_couriers: Sequence[Any],
    active_partner_by_platform: Mapping[str, Sequence[Any]],
    travel_model: Any,
    service_radius_meters: float | None,
    snapshot_cache: LegacyCourierSnapshotCache,
    geo_index: GeoIndex | None,
    speed_m_per_s: float,
) -> tuple[list[Any], list[Any]]:
    """Split backlog tasks into exact terminally infeasible and still-retriable sets.

    This helper is only intended for the post-arrival phase when future rounds
    can no longer receive new tasks. A task is marked terminal only when no
    local courier and no partner courier can satisfy the current feasibility
    checks.

    Args:
        unresolved_tasks: Tasks that survived the current matching round.
        now: Current batch time.
        active_local_couriers: Current local courier pool.
        active_partner_by_platform: Current partner courier pools.
        travel_model: Shared exact travel model.
        service_radius_meters: Optional courier-to-task radius limit.
        snapshot_cache: Reusable legacy-to-CAPA snapshot cache.
        geo_index: Optional geometric lower-bound index.
        speed_m_per_s: Exact travel speed used by the Chengdu graph model.

    Returns:
        `(terminal_tasks, retriable_tasks)` in the same task order.
    """

    from capa.cama import is_feasible_local_match
    from capa.dapa import is_feasible_cross_match

    terminal_tasks: list[Any] = []
    retriable_tasks: list[Any] = []
    local_snapshots = [
        snapshot_cache.get(courier, courier_id=local_courier_snapshot_id(courier))
        for courier in active_local_couriers
    ]
    partner_snapshots = {
        platform_id: [
            snapshot_cache.get(courier, courier_id=partner_courier_snapshot_id(platform_id, courier))
            for courier in couriers
        ]
        for platform_id, couriers in active_partner_by_platform.items()
    }
    for task in unresolved_tasks:
        parcel = legacy_task_to_parcel(task)
        feasible = any(
            is_feasible_local_match(
                parcel,
                courier,
                travel_model,
                now,
                service_radius_meters=service_radius_meters,
                geo_index=geo_index,
                speed_m_per_s=speed_m_per_s,
            )
            for courier in local_snapshots
        )
        if not feasible:
            feasible = any(
                is_feasible_cross_match(
                    parcel,
                    courier,
                    travel_model,
                    now,
                    service_radius_meters=service_radius_meters,
                    geo_index=geo_index,
                    speed_m_per_s=speed_m_per_s,
                )
                for couriers in partner_snapshots.values()
                for courier in couriers
            )
        if feasible:
            retriable_tasks.append(task)
        else:
            terminal_tasks.append(task)
    return terminal_tasks, retriable_tasks


def drain_legacy_routes(
    local_couriers: MutableSequence[Any],
    partner_couriers_by_platform: Mapping[str, MutableSequence[Any]],
    station_set: Sequence[Any],
    step_seconds: int,
    movement_callback: Callable[[MutableSequence[Any], MutableSequence[Any], int, Sequence[Any]], None],
) -> int:
    """Advance the simulator after the last batch until all accepted parcels are physically delivered."""
    drain_steps = 0
    while has_pending_legacy_routes(local_couriers, partner_couriers_by_platform):
        movement_callback(local_couriers, flatten_partner_couriers(partner_couriers_by_platform), step_seconds, station_set)
        drain_steps += 1
    return drain_steps


def _index_best_local_pairs(cama_result: Any) -> Dict[tuple[str, str], int]:
    """Map accepted local assignments back to their best insertion indices."""
    return {
        (pair.parcel.parcel_id, pair.courier.courier_id): pair.utility.insertion_index
        for pair in getattr(cama_result, "candidate_best_pairs", [])
    }


def _build_partner_lookup(partner_couriers_by_platform: Mapping[str, Sequence[Any]]) -> Dict[str, Dict[str, Any]]:
    """Index partner couriers by platform and synthesized courier identifier."""
    platform_lookup: Dict[str, Dict[str, Any]] = {}
    for platform_id, couriers in partner_couriers_by_platform.items():
        platform_lookup[platform_id] = {
            partner_courier_snapshot_id(platform_id, courier): courier for courier in couriers
        }
    return platform_lookup


def build_geo_index_from_travel_model(travel_model: Any) -> GeoIndex | None:
    """Build one reusable GeoIndex from the Chengdu travel model when available."""
    context = getattr(travel_model, "_context", None)
    nmap = None if context is None else getattr(context, "nMap", None)
    if nmap is None:
        return None
    return GeoIndex(nmap)


def get_travel_speed_m_per_s(travel_model: Any) -> float:
    """Return the travel speed encoded by the shared travel model, if any."""
    for attribute in ("_speed", "speed"):
        value = getattr(travel_model, attribute, None)
        if value is not None:
            return float(value)
    return 0.0


def run_time_stepped_chengdu_batches(
    tasks: Sequence[Any],
    local_couriers: Sequence[Any],
    partner_couriers_by_platform: Mapping[str, Sequence[Any]],
    station_set: Sequence[Any],
    travel_model: Any,
    config: CAPAConfig,
    batch_seconds: int,
    step_seconds: int,
    platform_base_prices: Mapping[str, float],
    platform_sharing_rates: Mapping[str, float],
    platform_qualities: Mapping[str, float],
    movement_callback: Callable[[MutableSequence[Any], MutableSequence[Any], int, Sequence[Any]], None] | None = None,
    service_radius_km: float | None = None,
    geo_index: GeoIndex | None = None,
    speed_m_per_s: float = 0.0,
    progress_callback: Callable[[Mapping[str, Any]], None] | None = None,
) -> CAPAResult:
    """Run CAPA over legacy Chengdu batches with one matching round per batch deadline."""
    if step_seconds <= 0:
        raise ValueError("Step duration must be positive.")

    active_local_couriers = list(local_couriers)
    active_partner_by_platform = {platform_id: list(couriers) for platform_id, couriers in partner_couriers_by_platform.items()}
    partner_lookup = _build_partner_lookup(active_partner_by_platform)
    batch_reports: List[BatchReport] = []
    matching_plan: List[Assignment] = []
    accepted_assignment_ids: set[str] = set()
    backlog: List[Any] = []
    terminal_unassigned: List[Any] = []
    first_batch_start, bucket_lookup = bucketize_legacy_tasks_by_batch(tasks, batch_seconds)
    if not bucket_lookup:
        return CAPAResult(
            matching_plan=[],
            unassigned_parcels=[],
            batch_reports=[],
            metrics=build_run_metrics([], 0, []),
            delivered_parcels=[],
        )

    movement = movement_callback or framework_movement_callback
    service_radius_meters = None if service_radius_km is None else float(service_radius_km) * 1000.0
    last_bucket_index = max(bucket_lookup)
    total_batches = last_bucket_index + 1
    current_time = first_batch_start
    batch_cursor = 0
    batch_index = 0
    persistent_travel_model = PersistentDirectedDistanceCache(travel_model)
    snapshot_cache = LegacyCourierSnapshotCache()
    insertion_cache = InsertionCache()

    while batch_cursor <= last_bucket_index or backlog:
        batch_index += 1
        batch_end_time = first_batch_start + ((batch_cursor + 1) * batch_seconds)
        elapsed_seconds = max(0, batch_end_time - current_time)
        timing = TimingAccumulator()
        if elapsed_seconds > 0:
            movement_started = perf_counter()
            movement(
                active_local_couriers,
                flatten_partner_couriers(active_partner_by_platform),
                elapsed_seconds,
                station_set,
            )
            timing.movement_time_seconds += perf_counter() - movement_started
        current_time = batch_end_time

        bucket = list(bucket_lookup.get(batch_cursor, []))
        batch_input_tasks = list(backlog) + bucket
        if not batch_input_tasks:
            batch_cursor += 1
            continue
        eligible_tasks = [task for task in batch_input_tasks if float(getattr(task, "d_time")) >= current_time]
        expired_tasks = [task for task in batch_input_tasks if float(getattr(task, "d_time")) < current_time]
        terminal_unassigned.extend(expired_tasks)
        if progress_callback is not None:
            progress_callback(
                {
                    "phase": "batch_matching",
                    "detail": format_batch_progress_label(batch_index, total_batches),
                    "batch_index": batch_index,
                    "total_batches": total_batches,
                    "batch_time": batch_end_time,
                    "completed_units": batch_index - 1,
                    "total_units": total_batches,
                    "unit_label": "batches",
                    "input_tasks": len(batch_input_tasks),
                    "eligible_tasks": len(eligible_tasks),
                    "backlog_tasks": len(backlog),
                }
            )
        if not eligible_tasks:
            batch_reports.append(
                BatchReport(
                    batch_index=batch_index,
                    batch_time=batch_end_time,
                    input_parcels=[legacy_task_to_parcel(task) for task in batch_input_tasks],
                    local_assignments=[],
                    cross_assignments=[],
                    unresolved_parcels=[],
                    processing_time_seconds=0.0,
                    timing=timing.freeze(),
                    delivered_parcel_count=len(
                        accepted_assignment_ids - current_legacy_route_task_ids(active_local_couriers, active_partner_by_platform)
                    ),
                )
            )
            backlog = []
            if progress_callback is not None:
                progress_callback(
                    {
                        "phase": "batch_completed",
                        "detail": format_batch_progress_label(batch_index, total_batches),
                        "batch_index": batch_index,
                        "total_batches": total_batches,
                        "completed_units": batch_index,
                        "total_units": total_batches,
                        "unit_label": "batches",
                        "local_assignments": 0,
                        "cross_assignments": 0,
                        "unresolved_tasks": 0,
                    }
                )
            batch_cursor += 1
            continue

        local_assignments: List[Assignment] = []
        cross_assignments: List[Assignment] = []
        processing_time_seconds = 0.0
        started = perf_counter()
        timed_travel_model = TimedTravelModel(persistent_travel_model, timing)
        local_snapshots = [
            snapshot_cache.get(courier, courier_id=local_courier_snapshot_id(courier))
            for courier in active_local_couriers
        ]
        insertion_cache.prune_to_active_routes(local_snapshots)
        batch_parcels = [legacy_task_to_parcel(task) for task in eligible_tasks]
        bdm = BatchDistanceMatrix(timed_travel_model)
        bdm.precompute_for_insertions(local_snapshots, batch_parcels)
        cama_result = run_cama(
            batch_parcels,
            local_snapshots,
            bdm,
            config,
            now=current_time,
            service_radius_meters=service_radius_meters,
            timing=timing,
            insertion_cache=insertion_cache,
            geo_index=geo_index,
            speed_m_per_s=speed_m_per_s,
            progress_callback=(
                None
                if progress_callback is None
                else lambda event, batch_index=batch_index, total_batches=total_batches: progress_callback(
                    {
                        **dict(event),
                        "detail": f"{format_batch_progress_label(batch_index, total_batches)} {event.get('detail', '')}".strip(),
                        "batch_index": batch_index,
                        "total_batches": total_batches,
                    }
                )
            ),
        )
        best_local_pairs = _index_best_local_pairs(cama_result)
        task_lookup = {parcel.parcel_id: task for parcel, task in zip(batch_parcels, eligible_tasks)}
        local_lookup = {local_courier_snapshot_id(courier): courier for courier in active_local_couriers}
        assigned_task_ids: set[int] = set()

        for assignment in cama_result.local_assignments:
            task = task_lookup[assignment.parcel.parcel_id]
            legacy_courier = local_lookup[assignment.courier.courier_id]
            insertion_index = best_local_pairs[(assignment.parcel.parcel_id, assignment.courier.courier_id)]
            apply_assignment_to_legacy_courier(task, legacy_courier, insertion_index)
            snapshot_cache.invalidate(assignment.courier.courier_id)
            insertion_cache.invalidate_courier(assignment.courier.courier_id)
            local_assignments.append(bind_assignment_to_legacy_objects(assignment, task, legacy_courier))
            assigned_task_ids.add(id(task))
            accepted_assignment_ids.add(str(getattr(task, "num")))

        remaining_tasks = [task for task in eligible_tasks if id(task) not in assigned_task_ids]
        if remaining_tasks:
            partner_platforms = [
                legacy_platform_to_capa(
                    platform_id=platform_id,
                    couriers=couriers,
                    base_price=platform_base_prices[platform_id],
                    sharing_rate_gamma=platform_sharing_rates[platform_id],
                    historical_quality=platform_qualities[platform_id],
                    snapshot_cache=snapshot_cache,
                )
                for platform_id, couriers in active_partner_by_platform.items()
            ]
            remaining_parcels = [legacy_task_to_parcel(task) for task in remaining_tasks]
            snapshot_lookup = {
                platform.platform_id: {courier.courier_id: courier for courier in platform.couriers}
                for platform in partner_platforms
            }
            partner_snapshots = [courier for platform in partner_platforms for courier in platform.couriers]
            insertion_cache.prune_to_active_routes([*local_snapshots, *partner_snapshots])
            bdm.precompute_for_insertions(partner_snapshots, remaining_parcels)
            dapa_result = run_dapa(
                remaining_parcels,
                partner_platforms,
                bdm,
                config,
                now=current_time,
                service_radius_meters=service_radius_meters,
                timing=timing,
                insertion_cache=insertion_cache,
                geo_index=geo_index,
                speed_m_per_s=speed_m_per_s,
                progress_callback=(
                    None
                    if progress_callback is None
                    else lambda event, batch_index=batch_index, total_batches=total_batches: progress_callback(
                        {
                            **dict(event),
                            "detail": f"{format_batch_progress_label(batch_index, total_batches)} {event.get('detail', '')}".strip(),
                            "batch_index": batch_index,
                            "total_batches": total_batches,
                        }
                    )
                ),
            )
            cross_task_lookup = {parcel.parcel_id: task for parcel, task in zip(remaining_parcels, remaining_tasks)}

            for assignment in dapa_result.cross_assignments:
                task = cross_task_lookup[assignment.parcel.parcel_id]
                legacy_courier = partner_lookup[assignment.platform_id][assignment.courier.courier_id]
                snapshot_courier = snapshot_lookup[assignment.platform_id][assignment.courier.courier_id]
                _, insertion_index = find_best_local_insertion(
                    legacy_task_to_parcel(task),
                    snapshot_courier,
                    bdm,
                    timing=timing,
                    insertion_cache=insertion_cache,
                    geo_index=geo_index,
                )
                apply_assignment_to_legacy_courier(task, legacy_courier, insertion_index)
                snapshot_cache.invalidate(assignment.courier.courier_id)
                insertion_cache.invalidate_courier(assignment.courier.courier_id)
                cross_assignments.append(bind_assignment_to_legacy_objects(assignment, task, legacy_courier))
                assigned_task_ids.add(id(task))
                accepted_assignment_ids.add(str(getattr(task, "num")))

        backlog = [task for task in eligible_tasks if id(task) not in assigned_task_ids]
        if backlog and batch_cursor >= last_bucket_index and not has_pending_legacy_routes(active_local_couriers, active_partner_by_platform):
            terminal_tasks, retriable_tasks = partition_terminal_backlog(
                unresolved_tasks=backlog,
                now=current_time,
                active_local_couriers=active_local_couriers,
                active_partner_by_platform=active_partner_by_platform,
                travel_model=timed_travel_model,
                service_radius_meters=service_radius_meters,
                snapshot_cache=snapshot_cache,
                geo_index=geo_index,
                speed_m_per_s=speed_m_per_s,
            )
            terminal_unassigned.extend(terminal_tasks)
            backlog = retriable_tasks
        processing_time_seconds += perf_counter() - started
        report = BatchReport(
            batch_index=batch_index,
            batch_time=batch_end_time,
                input_parcels=[legacy_task_to_parcel(task) for task in batch_input_tasks],
            local_assignments=local_assignments,
            cross_assignments=cross_assignments,
            unresolved_parcels=[legacy_task_to_parcel(task) for task in backlog],
            processing_time_seconds=processing_time_seconds,
            timing=timing.freeze(),
            delivered_parcel_count=len(accepted_assignment_ids - current_legacy_route_task_ids(active_local_couriers, active_partner_by_platform)),
        )
        batch_reports.append(report)
        if progress_callback is not None:
            progress_callback(
                {
                    "phase": "batch_completed",
                    "detail": format_batch_progress_label(batch_index, total_batches),
                    "batch_index": batch_index,
                    "total_batches": total_batches,
                    "completed_units": batch_index,
                    "total_units": total_batches,
                    "unit_label": "batches",
                    "local_assignments": len(local_assignments),
                    "cross_assignments": len(cross_assignments),
                    "unresolved_tasks": len(backlog),
                }
            )
        matching_plan.extend(local_assignments)
        matching_plan.extend(cross_assignments)
        batch_cursor += 1

    if backlog:
        terminal_unassigned.extend(backlog)
        batch_reports.append(
            BatchReport(
                batch_index=len(batch_reports) + 1,
                batch_time=batch_reports[-1].batch_time + batch_seconds,
                input_parcels=[legacy_task_to_parcel(task) for task in backlog],
                local_assignments=[],
                cross_assignments=[],
                unresolved_parcels=[legacy_task_to_parcel(task) for task in backlog],
                processing_time_seconds=0.0,
                timing=TimingAccumulator().freeze(),
            )
        )

    delivered_parcels: list[Parcel] = []
    if matching_plan:
        drain_legacy_routes(
            active_local_couriers,
            active_partner_by_platform,
            station_set,
            step_seconds,
            movement,
        )
        delivered_parcels = [assignment.parcel for assignment in matching_plan]

    return CAPAResult(
        matching_plan=matching_plan,
        unassigned_parcels=[legacy_task_to_parcel(task) for task in terminal_unassigned],
        batch_reports=batch_reports,
        metrics=build_run_metrics(matching_plan, len(tasks), batch_reports, delivered_parcel_count=len(delivered_parcels)),
        delivered_parcels=delivered_parcels,
    )


def format_batch_progress_label(batch_index: int, total_batches: int) -> str:
    """Format one user-facing batch progress label.

    Args:
        batch_index: One-based matching-round index.
        total_batches: Number of arrival windows induced by task times.

    Returns:
        Human-readable batch label that distinguishes carry-over rounds.
    """

    if batch_index <= total_batches:
        return f"window {batch_index}/{total_batches}"
    return f"retry {batch_index - total_batches}"


def build_framework_chengdu_environment(
    data_dir: Any,
    num_parcels: int,
    local_courier_count: int,
    cooperating_platform_count: int,
    couriers_per_platform: int,
    service_radius_km: float | None = None,
    courier_capacity: float | None = None,
) -> LegacyChengduEnvironment:
    """Build the official Chengdu experiment state from the repository's legacy framework."""
    import Framework_ChengDu as framework
    from Tasks_ChengDu import readTask

    pick_task_set, delivery_task_set = readTask()
    required_couriers = local_courier_count + (cooperating_platform_count * couriers_per_platform)
    ordered_pick = sort_legacy_tasks(pick_task_set)
    ordered_delivery = sort_legacy_tasks(delivery_task_set)
    framework.parameter_task_num = num_parcels
    normalized_capacity = 75 if courier_capacity is None else float(courier_capacity)
    framework.parameter_capacity = normalized_capacity
    framework.parameter_capacity_c = normalized_capacity
    station_blueprints = load_station_blueprints(str(Path(data_dir)), 11)

    station_set = []
    seeded_couriers: list[Any] = []
    station_by_num: dict[int, Any] = {}
    tasks: list[Any] = []
    framework.pick_task_set = []
    for delivery_seed_count in iter_delivery_seed_counts(required_couriers, len(ordered_delivery)):
        framework.delivery_task_set = ordered_delivery[:delivery_seed_count]
        framework.fw_ff_pick_task_set1 = []
        framework.fw_sum_time = 0
        station_set = instantiate_stations_from_blueprints(framework, station_blueprints)
        assign_delivery_tasks_to_stations(station_set, framework.delivery_task_set)
        available_seed_count = sum(len(getattr(station, "station_task_set", [])) for station in station_set)
        station_by_num = {station.num: station for station in station_set}
        seeded_couriers = generate_origin_schedule_with_retry(
            framework=framework,
            station_set=station_set,
            required_couriers=required_couriers,
            candidate_seed_count=available_seed_count,
            preference=0.5,
        )
        for courier in seeded_couriers:
            ensure_legacy_courier_station(courier, station_by_num)
            courier.batch_take = 0
        tasks = select_station_pick_tasks(station_set, ordered_pick, num_parcels)
        if len(seeded_couriers) >= required_couriers and len(tasks) >= num_parcels:
            break

    if len(seeded_couriers) < required_couriers:
        raise ValueError(
            f"Legacy framework produced only {len(seeded_couriers)} seeded couriers, fewer than the required {required_couriers}."
        )
    if len(tasks) < num_parcels:
        raise ValueError(
            f"Legacy framework produced only {len(tasks)} pick-up tasks inside station bounds, fewer than the requested {num_parcels}."
        )

    local_couriers = seeded_couriers[:local_courier_count]
    partner_couriers_by_platform: Dict[str, List[Any]] = {}
    offset = local_courier_count
    for platform_index in range(cooperating_platform_count):
        platform_id = f"P{platform_index + 1}"
        partner_couriers_by_platform[platform_id] = seeded_couriers[offset: offset + couriers_per_platform]
        offset += couriers_per_platform

    from capa.experiments import ChengduGraphTravelModel

    travel_model = ChengduGraphTravelModel()

    return LegacyChengduEnvironment(
        tasks=tasks,
        local_couriers=local_couriers,
        partner_couriers_by_platform=partner_couriers_by_platform,
        station_set=station_set,
        travel_model=travel_model,
        platform_base_prices={f"P{index + 1}": 1.0 for index in range(cooperating_platform_count)},
        platform_sharing_rates={f"P{index + 1}": 0.4 for index in range(cooperating_platform_count)},
        platform_qualities={f"P{index + 1}": max(0.5, 1.0 - 0.1 * index) for index in range(cooperating_platform_count)},
        movement_callback=framework_movement_callback,
        service_radius_km=service_radius_km,
        courier_capacity=normalized_capacity,
        geo_index=build_geo_index_from_travel_model(travel_model),
        travel_speed_m_per_s=get_travel_speed_m_per_s(travel_model),
    )
