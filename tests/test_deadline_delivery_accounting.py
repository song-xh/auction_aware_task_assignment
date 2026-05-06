"""Deadline-accurate delivery accounting regressions."""

from __future__ import annotations

from types import SimpleNamespace

from capa.models import CAPAConfig
from env.chengdu import ChengduEnvironment, run_time_stepped_chengdu_batches


class _TravelModel:
    """Minimal directed travel model for deadline-accounting tests."""

    speed = 1.0

    def distance(self, start: object, end: object) -> float:
        """Return one unit distance between distinct nodes."""

        if start == end:
            return 0.0
        return 1.0

    def travel_time(self, start: object, end: object) -> float:
        """Return travel time equal to the synthetic distance."""

        return self.distance(start, end)


def _task(task_id: str, *, release: int = 0, deadline: int = 100, fare: float = 10.0) -> SimpleNamespace:
    """Build one legacy-like pickup task."""

    return SimpleNamespace(
        num=task_id,
        l_node=f"node-{task_id}",
        s_time=float(release),
        d_time=float(deadline),
        weight=1.0,
        fare=float(fare),
    )


def _courier(*, available_from: int = 0) -> SimpleNamespace:
    """Build one legacy-like courier."""

    station = SimpleNamespace(num=1, l_node="depot")
    return SimpleNamespace(
        num=1,
        location="local",
        re_schedule=[],
        re_weight=0.0,
        max_weight=5.0,
        station=station,
        station_num=station.num,
        w=0.5,
        c=0.5,
        service_score=0.8,
        batch_take=0,
        available_from=float(available_from),
    )


def _complete_routes(
    local_couriers: list[SimpleNamespace],
    partner_couriers: list[SimpleNamespace],
    *_args: object,
) -> None:
    """Simulate one movement step by finishing every queued stop at step end."""

    for courier in [*local_couriers, *partner_couriers]:
        if courier.re_schedule:
            courier.location = courier.re_schedule[-1].l_node
        courier.re_schedule.clear()
        courier.re_weight = 0.0


def _environment(task: SimpleNamespace, *, available_from: int = 0) -> ChengduEnvironment:
    """Build one one-task Chengdu environment for metric tests."""

    station = SimpleNamespace(num=1, l_node="depot")
    courier = _courier(available_from=available_from)
    courier.station = station
    courier.station_num = station.num
    return ChengduEnvironment(
        tasks=[task],
        local_couriers=[courier],
        partner_couriers_by_platform={},
        station_set=[station],
        travel_model=_TravelModel(),
        platform_base_prices={},
        platform_sharing_rates={},
        platform_qualities={},
        movement_callback=_complete_routes,
        service_radius_km=None,
        travel_speed_m_per_s=1.0,
    )


def test_on_time_delivery_counts_as_delivered_and_revenue() -> None:
    """A parcel completed before the true deadline should count for TR and CR."""

    environment = _environment(_task("t1", deadline=100))
    result = run_time_stepped_chengdu_batches(
        tasks=environment.tasks,
        local_couriers=environment.local_couriers,
        partner_couriers_by_platform={},
        station_set=environment.station_set,
        travel_model=environment.travel_model,
        config=CAPAConfig(batch_size=30),
        batch_seconds=30,
        step_seconds=60,
        platform_base_prices={},
        platform_sharing_rates={},
        platform_qualities={},
        movement_callback=environment.movement_callback,
        speed_m_per_s=1.0,
    )

    assert result.metrics.delivered_parcel_count == 1
    assert result.metrics.timed_out_parcel_count == 0
    assert result.metrics.total_revenue > 0.0


def test_accepted_but_late_delivery_becomes_timeout() -> None:
    """A parcel accepted before its deadline but completed after it should time out."""

    environment = _environment(_task("t1", deadline=50))
    result = run_time_stepped_chengdu_batches(
        tasks=environment.tasks,
        local_couriers=environment.local_couriers,
        partner_couriers_by_platform={},
        station_set=environment.station_set,
        travel_model=environment.travel_model,
        config=CAPAConfig(batch_size=30),
        batch_seconds=30,
        step_seconds=60,
        platform_base_prices={},
        platform_sharing_rates={},
        platform_qualities={},
        movement_callback=environment.movement_callback,
        speed_m_per_s=1.0,
    )

    assert result.metrics.accepted_parcel_count == 1
    assert result.metrics.delivered_parcel_count == 0
    assert result.metrics.timed_out_parcel_count == 1
    assert result.metrics.total_revenue == 0.0


def test_batch_waiting_time_counts_toward_true_completion_time() -> None:
    """Long batch waiting before acceptance should still count toward timeout."""

    environment = _environment(_task("t1", deadline=100))
    result = run_time_stepped_chengdu_batches(
        tasks=environment.tasks,
        local_couriers=environment.local_couriers,
        partner_couriers_by_platform={},
        station_set=environment.station_set,
        travel_model=environment.travel_model,
        config=CAPAConfig(batch_size=90),
        batch_seconds=90,
        step_seconds=60,
        platform_base_prices={},
        platform_sharing_rates={},
        platform_qualities={},
        movement_callback=environment.movement_callback,
        speed_m_per_s=1.0,
    )

    assert result.metrics.accepted_parcel_count == 1
    assert result.metrics.delivered_parcel_count == 0
    assert result.metrics.timed_out_parcel_count == 1
