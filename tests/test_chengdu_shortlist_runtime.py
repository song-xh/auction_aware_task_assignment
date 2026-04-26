"""Tests for shortlist wiring in the formal Chengdu CAPA runtime."""

from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import patch

from capa.models import Assignment, CAPAConfig, CAMAResult, CandidatePair, UtilityEvaluation
from env.chengdu import run_time_stepped_chengdu_batches

from tests.capa_test_support import FakeGeoIndex, FakeTravelModel


def _build_station(node: str = "depot") -> SimpleNamespace:
    """Return a minimal legacy station object for Chengdu runtime tests."""

    return SimpleNamespace(num=1, l_node=node)


def _build_task(
    num: int,
    location: str,
    s_time: int = 0,
    d_time: int = 100,
    weight: float = 1.0,
    fare: float = 10.0,
) -> SimpleNamespace:
    """Return a minimal legacy task object for Chengdu runtime tests."""

    return SimpleNamespace(
        num=num,
        l_node=location,
        s_time=s_time,
        d_time=d_time,
        weight=weight,
        fare=fare,
    )


def _build_courier(
    num: int,
    station: SimpleNamespace,
    location: str,
    *,
    max_weight: float = 10.0,
) -> SimpleNamespace:
    """Return a minimal legacy courier object for Chengdu runtime tests."""

    return SimpleNamespace(
        num=num,
        location=location,
        max_weight=max_weight,
        re_weight=0.0,
        re_schedule=[],
        station=station,
        w=0.5,
        c=0.5,
        service_score=0.8,
        batch_take=0,
        available_from=0,
    )


def _draining_movement(local_couriers, partner_couriers, seconds, station_set) -> None:
    """Advance the fake simulator by clearing any pending legacy route buffers."""

    del seconds, station_set
    for courier in [*local_couriers, *partner_couriers]:
        courier.re_schedule.clear()
        courier.re_weight = 0.0


class ChengduShortlistRuntimeTest(unittest.TestCase):
    """Verify shortlist pruning is wired into the formal Chengdu runtime."""

    def test_local_runtime_passes_shortlist_to_cama_and_warms_only_shortlisted_pairs(self) -> None:
        """Formal Chengdu local CAPA path should prune before exact warmup and CAMA."""

        station = _build_station()
        task = _build_task(1, "parcel")
        near = _build_courier(1, station, "near")
        far = _build_courier(2, station, "far")
        travel_model = FakeTravelModel(
            distances={
                ("near", "depot"): 4.0,
                ("near", "parcel"): 2.0,
                ("parcel", "depot"): 2.0,
                ("far", "depot"): 4.0,
                ("far", "parcel"): 8.0,
            }
        )
        geo_index = FakeGeoIndex(
            lower_bounds={
                ("near", "parcel"): 5.0,
                ("far", "parcel"): 50.0,
            }
        )
        captured: dict[str, object] = {}

        def fake_run_cama(parcels, couriers, travel_model, config, now, **kwargs):  # type: ignore[no-untyped-def]
            candidate_shortlist = kwargs.get("candidate_couriers_by_parcel")
            captured["shortlist"] = candidate_shortlist
            pair = CandidatePair(
                parcel=parcels[0],
                courier=candidate_shortlist[parcels[0].parcel_id][0],
                utility=UtilityEvaluation(
                    value=1.0,
                    capacity_ratio=1.0,
                    detour_ratio=1.0,
                    insertion_index=0,
                ),
            )
            assignment = Assignment(
                parcel=pair.parcel,
                courier=pair.courier,
                mode="local",
                platform_id=None,
                courier_payment=1.0,
                platform_payment=1.0,
                local_platform_revenue=1.0,
                cooperating_platform_revenue=0.0,
                courier_revenue=1.0,
                utility_value=1.0,
            )
            return CAMAResult(
                local_assignments=[assignment],
                auction_pool=[],
                all_feasible_pairs=[pair],
                candidate_best_pairs=[pair],
                threshold=0.0,
                matching_pairs=[assignment],
            )

        with patch("env.chengdu.run_cama", side_effect=fake_run_cama):
            run_time_stepped_chengdu_batches(
                tasks=[task],
                local_couriers=[near, far],
                partner_couriers_by_platform={},
                station_set=[station],
                travel_model=travel_model,
                config=CAPAConfig(),
                batch_seconds=10,
                step_seconds=10,
                platform_base_prices={},
                platform_sharing_rates={},
                platform_qualities={},
                movement_callback=_draining_movement,
                service_radius_km=0.01,
                geo_index=geo_index,
                speed_m_per_s=1.0,
            )

        shortlist = captured["shortlist"]
        self.assertEqual(
            [courier.courier_id for courier in shortlist["1"]],
            ["local-1"],
        )
        self.assertNotIn(("far", "depot"), travel_model.distance_calls)
        self.assertNotIn(("far", "parcel"), travel_model.distance_calls)


if __name__ == "__main__":
    unittest.main()
