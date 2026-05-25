"""Regression tests for deadline-disturbance experiment semantics."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, MutableSequence, Sequence

from capa.models import CAPAConfig
from env.chengdu import (
    ChengduBatchRuntime,
    ChengduEnvironment,
    get_model_deadline,
    get_model_release_time,
    get_true_deadline,
    legacy_task_to_parcel,
    prepare_chengdu_batch,
)
from experiments.deadline_disturbance import (
    apply_deadline_noise,
    apply_processing_delay,
    derive_deadline_delay_environment,
    derive_deadline_noise_environment,
)
from experiments.seeding import build_environment_seed


def test_observed_time_helpers_preserve_true_deadline() -> None:
    """Observed fields should affect model-facing values without replacing d_time."""

    task = SimpleNamespace(
        num="t1",
        s_time=10.0,
        d_time=100.0,
        observed_s_time=15.0,
        observed_d_time=80.0,
    )

    assert get_model_release_time(task) == 15.0
    assert get_model_deadline(task) == 80.0
    assert get_true_deadline(task) == 100.0


def test_legacy_task_to_parcel_can_use_observed_deadline() -> None:
    """Parcel conversion should expose observed deadlines while preserving true access."""

    task = SimpleNamespace(
        num="t1",
        s_time=10.0,
        d_time=100.0,
        observed_d_time=80.0,
        weight=1.0,
        fare=20.0,
        l_node="A",
    )

    assert legacy_task_to_parcel(task).deadline == 80
    assert legacy_task_to_parcel(task, use_observed_deadline=False).deadline == 100


def test_prepare_batch_uses_observed_release_and_true_expiration() -> None:
    """Batching should delay visibility but expire by the true deadline."""

    visible_later = SimpleNamespace(
        num="t1",
        s_time=0.0,
        d_time=100.0,
        observed_s_time=15.0,
        weight=1.0,
        fare=20.0,
        l_node="A",
    )
    already_expired = SimpleNamespace(
        num="t2",
        s_time=0.0,
        d_time=5.0,
        observed_s_time=0.0,
        observed_d_time=100.0,
        weight=1.0,
        fare=20.0,
        l_node="B",
    )
    runtime = _runtime([already_expired, visible_later])

    first = prepare_chengdu_batch(runtime, 10)
    assert [task.num for task in first.input_tasks] == ["t2"]
    assert [task.num for task in first.expired_tasks] == ["t2"]

    second = prepare_chengdu_batch(runtime, 10)
    assert [task.num for task in second.input_tasks] == ["t1"]
    assert [task.num for task in second.eligible_tasks] == ["t1"]


def test_apply_deadline_delay_sets_observed_release_only() -> None:
    """Exp-7 delay should not mutate original release or deadline fields."""

    task = SimpleNamespace(num="t1", s_time=10.0, d_time=100.0)

    apply_processing_delay([task], delay_seconds=20)

    assert task.s_time == 10.0
    assert task.d_time == 100.0
    assert task.observed_s_time == 30.0


def test_derive_deadline_delay_environment_mutates_only_clone() -> None:
    """Exp-7 environment derivation should keep canonical seeds reusable."""

    task = SimpleNamespace(num="t1", s_time=10.0, d_time=100.0)
    seed = build_environment_seed(
        ChengduEnvironment(
            tasks=[task],
            local_couriers=[],
            partner_couriers_by_platform={},
            station_set=[],
            travel_model=None,
            platform_base_prices={},
            platform_sharing_rates={},
            platform_qualities={},
        )
    )

    derived = derive_deadline_delay_environment(seed, delay_seconds=5)

    assert not hasattr(task, "observed_s_time")
    assert derived.tasks[0].observed_s_time == 15.0
    assert derived.tasks[0].d_time == 100.0


def test_apply_deadline_noise_uses_slack_and_preserves_true_deadline() -> None:
    """Exp-8 positive noise should extend only the model-facing deadline."""

    task = SimpleNamespace(num="t1", s_time=10.0, d_time=110.0)

    apply_deadline_noise([task], noise_percent=20)

    assert task.d_time == 110.0
    assert task.observed_d_time == 130.0


def test_apply_deadline_noise_supports_early_observed_deadline() -> None:
    """Exp-8 negative noise should tighten only the model-facing deadline."""

    task = SimpleNamespace(num="t1", s_time=10.0, d_time=110.0)

    apply_deadline_noise([task], noise_percent=-20)

    assert task.d_time == 110.0
    assert task.observed_d_time == 90.0


def test_derive_deadline_noise_environment_mutates_only_clone() -> None:
    """Exp-8 environment derivation should keep canonical seeds reusable."""

    task = SimpleNamespace(num="t1", s_time=10.0, d_time=110.0)
    seed = build_environment_seed(
        ChengduEnvironment(
            tasks=[task],
            local_couriers=[],
            partner_couriers_by_platform={},
            station_set=[],
            travel_model=None,
            platform_base_prices={},
            platform_sharing_rates={},
            platform_qualities={},
        )
    )

    derived = derive_deadline_noise_environment(seed, noise_percent=10)

    assert not hasattr(task, "observed_d_time")
    assert derived.tasks[0].observed_d_time == 120.0
    assert derived.tasks[0].d_time == 110.0


def test_apply_deadline_noise_window_skips_out_of_window_tasks() -> None:
    """Tasks outside the noise window should get observed_d_time == true deadline."""

    in_window = SimpleNamespace(num="t1", s_time=400.0, d_time=700.0)
    out_of_window = SimpleNamespace(num="t2", s_time=100.0, d_time=500.0)

    apply_deadline_noise([in_window, out_of_window], noise_percent=20, window=(300.0, 600.0))

    assert in_window.observed_d_time == 700.0 + round(300.0 * 0.2)  # 760
    assert in_window.is_noised is True
    assert out_of_window.observed_d_time == 500.0
    assert out_of_window.is_noised is False


def test_apply_deadline_noise_window_none_applies_to_all() -> None:
    """When window is None, all tasks receive noise (original behavior)."""

    t1 = SimpleNamespace(num="t1", s_time=10.0, d_time=110.0)
    t2 = SimpleNamespace(num="t2", s_time=500.0, d_time=800.0)

    apply_deadline_noise([t1, t2], noise_percent=10)

    assert t1.observed_d_time == 110.0 + round(100.0 * 0.1)  # 120
    assert t2.observed_d_time == 800.0 + round(300.0 * 0.1)  # 830


def _runtime(tasks: Sequence[Any]) -> ChengduBatchRuntime:
    """Build a minimal batch runtime for deadline-disturbance tests."""

    def no_movement(
        local_couriers: MutableSequence[Any],
        partner_couriers: MutableSequence[Any],
        step_seconds: int,
        station_set: Sequence[Any],
    ) -> None:
        """Leave all couriers stationary in unit tests."""

        del local_couriers, partner_couriers, step_seconds, station_set

    return ChengduBatchRuntime(
        sorted_tasks=list(tasks),
        active_local_couriers=[],
        active_partner_by_platform={},
        station_set=[],
        travel_model=None,
        config=CAPAConfig(),
        movement=no_movement,
        platform_base_prices={},
        platform_sharing_rates={},
        platform_qualities={},
        service_radius_meters=None,
        geo_index=None,
        speed_m_per_s=1.0,
        step_seconds=10,
        current_time=0,
    )
