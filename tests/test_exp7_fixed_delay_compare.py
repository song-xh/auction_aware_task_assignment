"""Tests for fixed-data Exp-7 delay comparison helpers."""

from __future__ import annotations

import csv
from pathlib import Path
from types import SimpleNamespace

from algorithms.impgta_runner import ImpGTARunner
import experiments.exp7_fixed_delay_compare as fixed_delay_compare
import experiments.run_chengdu_exp7_fixed_delay_compare as fixed_delay_script
from experiments.exp7_fixed_delay_compare import (
    export_exp7_delay_datasets,
    prepare_exp7_delay_datasets,
    resolve_canonical_environment,
    summarize_delay_run,
)


def _task(num: str, s_time: float, d_time: float) -> SimpleNamespace:
    """Build one minimal legacy-task stub for export/comparison tests."""

    return SimpleNamespace(
        num=num,
        s_time=s_time,
        d_time=d_time,
        weight=1.0,
        fare=10.0,
        l_node=f"node-{num}",
        l_lng=104.0,
        l_lat=30.0,
    )


def test_export_exp7_delay_datasets_writes_canonical_and_delayed_csvs(tmp_path: Path) -> None:
    """Canonical local tasks, delayed variants, and partner streams should be exported."""

    environment = SimpleNamespace(
        tasks=[_task("p1", 5.0, 100.0), _task("p2", 20.0, 120.0)],
        partner_tasks_by_platform={
            "P1": [_task("q1", 7.0, 110.0)],
            "P2": [_task("q2", 25.0, 140.0)],
        },
    )

    manifest = export_exp7_delay_datasets(
        canonical_environment=environment,
        data_cache_dir=tmp_path,
        delay_values=[5, 10],
        delay_window=(10.0, 30.0),
    )

    assert Path(manifest["canonical_pickup_path"]).exists()
    assert Path(manifest["partner_task_paths"]["P1"]).exists()
    assert Path(manifest["delayed_pickup_paths"]["5"]).exists()
    assert Path(manifest["delayed_pickup_paths"]["10"]).exists()

    with Path(manifest["delayed_pickup_paths"]["5"]).open("r", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert [row["parcel_id"] for row in rows] == ["p1", "p2"]
    assert rows[0]["true_release_time"] == "5.0"
    assert rows[0]["observed_release_time"] == "5.0"
    assert rows[0]["is_delayed"] == "False"
    assert rows[1]["true_release_time"] == "20.0"
    assert rows[1]["observed_release_time"] == "25.0"
    assert rows[1]["is_delayed"] == "True"


def test_prepare_exp7_delay_datasets_reuse_requires_existing_manifest(tmp_path: Path) -> None:
    """Reuse mode should fail clearly when the cached dataset manifest is missing."""

    environment = SimpleNamespace(tasks=[_task("p1", 5.0, 100.0)], partner_tasks_by_platform={})

    try:
        prepare_exp7_delay_datasets(
            canonical_environment=environment,
            data_cache_dir=tmp_path,
            delay_values=[5],
            delay_window=(10.0, 30.0),
            data_mode="reuse",
        )
    except FileNotFoundError as exc:
        assert "manifest.json" in str(exc)
    else:
        raise AssertionError("Expected reuse mode to require an existing manifest.")


def test_prepare_exp7_delay_datasets_reuses_existing_manifest_without_rewrite(tmp_path: Path) -> None:
    """Reuse mode should keep existing exported data untouched."""

    environment = SimpleNamespace(tasks=[_task("p1", 5.0, 100.0)], partner_tasks_by_platform={})
    first_manifest = export_exp7_delay_datasets(
        canonical_environment=environment,
        data_cache_dir=tmp_path,
        delay_values=[5],
        delay_window=(10.0, 30.0),
    )
    pickup_path = Path(first_manifest["canonical_pickup_path"])
    pickup_path.write_text("sentinel\n", encoding="utf-8")

    reused_manifest = prepare_exp7_delay_datasets(
        canonical_environment=environment,
        data_cache_dir=tmp_path,
        delay_values=[5],
        delay_window=(10.0, 30.0),
        data_mode="reuse",
    )

    assert reused_manifest == first_manifest
    assert pickup_path.read_text(encoding="utf-8") == "sentinel\n"


def test_prepare_exp7_delay_datasets_auto_prefers_existing_manifest(tmp_path: Path) -> None:
    """Auto mode should reuse existing cached data when a manifest is already present."""

    environment = SimpleNamespace(tasks=[_task("p1", 5.0, 100.0)], partner_tasks_by_platform={})
    manifest = export_exp7_delay_datasets(
        canonical_environment=environment,
        data_cache_dir=tmp_path,
        delay_values=[5],
        delay_window=(10.0, 30.0),
    )
    pickup_path = Path(manifest["canonical_pickup_path"])
    pickup_path.write_text("sentinel\n", encoding="utf-8")

    auto_manifest = prepare_exp7_delay_datasets(
        canonical_environment=environment,
        data_cache_dir=tmp_path,
        delay_values=[5],
        delay_window=(10.0, 30.0),
        data_mode="auto",
    )

    assert auto_manifest == manifest
    assert pickup_path.read_text(encoding="utf-8") == "sentinel\n"


def test_resolve_canonical_environment_reuses_cached_seed(tmp_path: Path) -> None:
    """Reuse mode should load the cached canonical seed instead of the passed environment."""

    cached_environment = SimpleNamespace(
        tasks=[_task("cached", 5.0, 100.0)],
        local_couriers=[],
        partner_couriers_by_platform={},
        partner_tasks_by_platform={},
        station_set=[],
        travel_model=None,
        platform_base_prices={},
        platform_sharing_rates={},
        platform_qualities={},
        movement_callback=None,
        service_radius_km=None,
        courier_capacity=None,
        task_window_start_seconds=None,
        task_window_end_seconds=None,
        task_sampling_seed=1,
        courier_alpha=0.5,
        courier_beta=0.5,
        courier_service_score=1.0,
        platform_quality_start=1.0,
        platform_quality_step=0.1,
        geo_index=None,
        travel_speed_m_per_s=0.0,
        deadline_seconds=None,
        courier_speed_kmh=None,
    )
    current_environment = SimpleNamespace(
        tasks=[_task("current", 6.0, 120.0)],
        local_couriers=[],
        partner_couriers_by_platform={},
        partner_tasks_by_platform={},
        station_set=[],
        travel_model=None,
        platform_base_prices={},
        platform_sharing_rates={},
        platform_qualities={},
        movement_callback=None,
        service_radius_km=None,
        courier_capacity=None,
        task_window_start_seconds=None,
        task_window_end_seconds=None,
        task_sampling_seed=1,
        courier_alpha=0.5,
        courier_beta=0.5,
        courier_service_score=1.0,
        platform_quality_start=1.0,
        platform_quality_step=0.1,
        geo_index=None,
        travel_speed_m_per_s=0.0,
        deadline_seconds=None,
        courier_speed_kmh=None,
    )
    manifest = export_exp7_delay_datasets(
        canonical_environment=cached_environment,
        data_cache_dir=tmp_path,
        delay_values=[5],
        delay_window=(10.0, 30.0),
    )

    resolved = resolve_canonical_environment(
        canonical_environment=current_environment,
        data_manifest=manifest,
        data_mode="reuse",
    )

    assert [task.num for task in resolved.tasks] == ["cached"]


def test_summarize_delay_run_reports_metric_deltas_and_affected_outcomes() -> None:
    """Per-delay summaries should compare metrics and affected outcomes vs baseline."""

    baseline_summary = {
        "metrics": {
            "TR": 100.0,
            "CR": 1.0,
            "BPT": 0.4,
            "delivered_parcels": 2,
            "accepted_assignments": 2,
            "timed_out_parcels": 0,
        },
        "decision_trace": [
            {"parcel_id": "p1", "mode": "local", "delivered": True, "on_time": True},
            {"parcel_id": "p2", "mode": "local", "delivered": True, "on_time": True},
        ],
    }
    delayed_summary = {
        "metrics": {
            "TR": 92.0,
            "CR": 0.5,
            "BPT": 0.6,
            "delivered_parcels": 1,
            "accepted_assignments": 2,
            "timed_out_parcels": 1,
        },
        "decision_trace": [
            {"parcel_id": "p1", "mode": "cross", "delivered": True, "on_time": True},
            {"parcel_id": "p2", "mode": "local", "delivered": False, "on_time": False},
        ],
    }

    comparison = summarize_delay_run(
        baseline_summary=baseline_summary,
        delayed_summary=delayed_summary,
        affected_parcel_ids=["p1", "p2"],
    )

    assert comparison["metric_deltas"] == {
        "TR": -8.0,
        "CR": -0.5,
        "BPT": 0.2,
        "delivered_parcels": -1,
        "accepted_assignments": 0,
        "timed_out_parcels": 1,
    }
    assert comparison["transition_counts"] == {
        "delivered_local__delivered_cross": 1,
        "delivered_local__timed_out": 1,
    }
    assert comparison["affected_outcome_totals"]["baseline"] == {
        "delivered_local": 2,
        "delivered_cross": 0,
        "timed_out": 0,
        "unmatched": 0,
        "missing": 0,
    }
    assert comparison["affected_outcome_totals"]["delayed"] == {
        "delivered_local": 0,
        "delivered_cross": 1,
        "timed_out": 1,
        "unmatched": 0,
        "missing": 0,
    }


def test_impgta_runner_carries_decision_trace_into_summary(tmp_path: Path) -> None:
    """ImpGTA summaries must expose decision_trace for affected-parcel comparisons."""

    runner = ImpGTARunner(
        baseline_runner=lambda **_: {
            "TR": 50.0,
            "CR": 0.5,
            "BPT": 0.1,
            "delivered_parcels": 1,
            "accepted_assignments": 1,
            "timed_out_parcels": 0,
            "local_assignment_count": 1,
            "cross_assignment_count": 0,
            "unresolved_parcel_count": 1,
            "partner_cross_assignment_counts": {},
            "partner_cross_revenues": {},
            "decision_trace": [
                {
                    "parcel_id": "p1",
                    "mode": "local",
                    "courier_id": "c1",
                    "delivered": True,
                    "on_time": True,
                    "local_platform_revenue": 8.0,
                }
            ],
        }
    )
    environment = SimpleNamespace(tasks=[_task("p1", 5.0, 100.0), _task("p2", 6.0, 120.0)])

    summary = runner.run(environment=environment, output_dir=tmp_path)

    assert summary["decision_trace"] == [
        {
            "parcel_id": "p1",
            "mode": "local",
            "courier_id": "c1",
            "delivered": True,
            "on_time": True,
            "local_platform_revenue": 8.0,
        }
    ]


def test_run_exp7_fixed_delay_compare_builds_each_delay_seed_once(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Delayed environment seeds should be built once per point, not once per algorithm."""

    environment = SimpleNamespace(tasks=[_task("p1", 5.0, 100.0)])
    build_calls: list[str] = []

    def fake_prepare(**_: object) -> dict[str, object]:
        return {"seed_path": None}

    def fake_resolve(**_: object) -> SimpleNamespace:
        return environment

    def fake_build_seed(current_environment: object) -> dict[str, object]:
        build_calls.append(str(id(current_environment)))
        return {"environment": current_environment}

    def fake_clone(seed: dict[str, object]) -> SimpleNamespace:
        current_environment = seed["environment"]
        return SimpleNamespace(tasks=list(getattr(current_environment, "tasks", [])))

    def fake_run_one_algorithm(**_: object) -> dict[str, object]:
        return {"metrics": {}, "decision_trace": []}

    monkeypatch.setattr(fixed_delay_compare, "prepare_exp7_delay_datasets", fake_prepare)
    monkeypatch.setattr(fixed_delay_compare, "resolve_canonical_environment", fake_resolve)
    monkeypatch.setattr(fixed_delay_compare, "build_environment_seed", fake_build_seed)
    monkeypatch.setattr(fixed_delay_compare, "clone_environment_from_seed", fake_clone)
    monkeypatch.setattr(fixed_delay_compare, "apply_processing_delay", lambda *args, **kwargs: None)
    monkeypatch.setattr(fixed_delay_compare, "_affected_parcel_ids", lambda *_args, **_kwargs: ["p1"])
    monkeypatch.setattr(fixed_delay_compare, "_run_one_algorithm", fake_run_one_algorithm)

    fixed_delay_compare.run_exp7_fixed_delay_compare(
        canonical_environment=environment,
        delay_values=[5, 10],
        delay_window=(10.0, 20.0),
        algorithms=["capa", "ramcom"],
        output_dir=tmp_path / "outputs",
        data_cache_dir=tmp_path / "data",
    )

    assert len(build_calls) == 3


def test_fixed_delay_script_dispatches_split_execution_mode(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """The fixed Exp-7 CLI should honor split execution like the paper sweep scripts."""

    calls: list[tuple[str, dict[str, object]]] = []

    def fake_split(**kwargs: object) -> dict[str, object]:
        calls.append(("split", dict(kwargs)))
        return {}

    def fail_direct(**_: object) -> dict[str, object]:
        raise AssertionError("direct runner should not be used in split mode")

    monkeypatch.setattr(fixed_delay_script, "run_exp7_fixed_delay_split_experiment", fake_split)
    monkeypatch.setattr(fixed_delay_script, "run_exp7_fixed_delay_direct", fail_direct)
    monkeypatch.setattr(
        fixed_delay_script,
        "_build_canonical_environment",
        lambda fixed_config: SimpleNamespace(tasks=[]),
    )
    monkeypatch.setattr(
        fixed_delay_script.sys,
        "argv",
        [
            "run_chengdu_exp7_fixed_delay_compare.py",
            "--execution-mode",
            "split",
            "--output-dir",
            str(tmp_path / "outputs"),
            "--delay-window",
            "10,20",
            "--algorithms",
            "capa",
            "--data-cache-dir",
            str(tmp_path / "data"),
        ],
    )

    assert fixed_delay_script.main() == 0
    assert calls
    assert calls[0][0] == "split"
