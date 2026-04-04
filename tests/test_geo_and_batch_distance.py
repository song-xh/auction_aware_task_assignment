"""Tests for geometric pre-filtering and batch distance matrix."""

from __future__ import annotations

import unittest

from capa.batch_distance import BatchDistanceMatrix
from capa.constraints import is_deadline_feasible_by_geo, is_within_service_radius
from capa.geo import GeoIndex, haversine_meters
from capa.models import Courier, Parcel
from capa.utility import find_best_local_insertion


class _FakeNode:
    def __init__(self, node_id: str, lat: float, lng: float):
        self.nodeId = node_id
        self.lat = lat
        self.lng = lng


class _FakeTravelModel:
    def __init__(self, distances: dict[tuple[str, str], float], speed: float = 1.0):
        self._distances = distances
        self.speed = speed

    def distance(self, a, b):
        if a == b:
            return 0.0
        return self._distances.get((a, b)) or self._distances.get((b, a)) or 999999.0

    def travel_time(self, a, b):
        return self.distance(a, b) / self.speed


class _CountingTravelModel:
    def __init__(self, distances: dict[tuple[str, str], float], speed: float = 1.0):
        self._distances = distances
        self.speed = speed
        self.calls: list[tuple[str, str]] = []

    def distance(self, a, b):
        self.calls.append((a, b))
        if a == b:
            return 0.0
        if (a, b) not in self._distances:
            raise KeyError((a, b))
        return self._distances[(a, b)]

    def travel_time(self, a, b):
        return self.distance(a, b) / self.speed


class TestHaversine(unittest.TestCase):
    def test_same_point_is_zero(self):
        self.assertAlmostEqual(haversine_meters(30.0, 104.0, 30.0, 104.0), 0.0)

    def test_known_distance(self):
        # Chengdu center (~30.57, 104.07) to ~30.67, 104.07 is roughly 11 km
        d = haversine_meters(30.57, 104.07, 30.67, 104.07)
        self.assertGreater(d, 10000)
        self.assertLess(d, 12000)


class TestGeoIndex(unittest.TestCase):
    def setUp(self):
        nmap = {
            "A": _FakeNode("A", 30.0, 104.0),
            "B": _FakeNode("B", 30.1, 104.0),
            "C": _FakeNode("C", 30.0, 104.1),
        }
        self.geo = GeoIndex(nmap)

    def test_lookup(self):
        self.assertIsNotNone(self.geo.get("A"))
        self.assertIsNone(self.geo.get("Z"))

    def test_haversine_between(self):
        d = self.geo.haversine_meters_between("A", "B")
        self.assertIsNotNone(d)
        self.assertGreater(d, 0)

    def test_unknown_node_returns_none(self):
        self.assertIsNone(self.geo.haversine_meters_between("A", "Z"))


class TestGeoPreFilter(unittest.TestCase):
    def setUp(self):
        nmap = {
            "near": _FakeNode("near", 30.0, 104.0),
            "far": _FakeNode("far", 31.0, 105.0),
            "task": _FakeNode("task", 30.001, 104.001),
        }
        self.geo = GeoIndex(nmap)

    def test_service_radius_rejects_far_courier(self):
        model = _FakeTravelModel({("far", "task"): 200_000.0})
        result = is_within_service_radius("far", "task", model, 5000.0, geo_index=self.geo)
        self.assertFalse(result)

    def test_service_radius_accepts_near_courier(self):
        model = _FakeTravelModel({("near", "task"): 100.0})
        result = is_within_service_radius("near", "task", model, 5000.0, geo_index=self.geo)
        self.assertTrue(result)

    def test_deadline_rejects_far_courier(self):
        result = is_deadline_feasible_by_geo("far", "task", now=0, deadline=10, speed_m_per_s=1.0, geo_index=self.geo)
        self.assertFalse(result)

    def test_deadline_accepts_near_courier(self):
        result = is_deadline_feasible_by_geo("near", "task", now=0, deadline=99999, speed_m_per_s=1.0, geo_index=self.geo)
        self.assertTrue(result)

    def test_no_geo_index_is_optimistic(self):
        result = is_deadline_feasible_by_geo("far", "task", now=0, deadline=1, speed_m_per_s=1.0, geo_index=None)
        self.assertTrue(result)


class TestBatchDistanceMatrix(unittest.TestCase):
    def setUp(self):
        self.model = _FakeTravelModel({
            ("A", "B"): 100.0,
            ("A", "C"): 200.0,
            ("B", "C"): 150.0,
        }, speed=10.0)

    def test_precompute_and_lookup(self):
        bdm = BatchDistanceMatrix(self.model)
        bdm.precompute(["A", "B", "C"])
        self.assertEqual(bdm.distance("A", "B"), 100.0)
        self.assertEqual(bdm.distance("B", "A"), 100.0)
        self.assertEqual(bdm.distance("A", "A"), 0.0)

    def test_precompute_preserves_directed_distances(self):
        model = _CountingTravelModel({
            ("A", "B"): 100.0,
            ("B", "A"): 180.0,
        })
        bdm = BatchDistanceMatrix(model)
        bdm.precompute(["A", "B"])

        self.assertEqual(bdm.distance("A", "B"), 100.0)
        self.assertEqual(bdm.distance("B", "A"), 180.0)

    def test_fallback_on_miss(self):
        bdm = BatchDistanceMatrix(self.model)
        bdm.precompute(["A"])  # only self-distance
        # "A","B" not precomputed but should fall through
        self.assertEqual(bdm.distance("A", "B"), 100.0)

    def test_travel_time_delegates(self):
        bdm = BatchDistanceMatrix(self.model)
        self.assertAlmostEqual(bdm.travel_time("A", "B"), 10.0)

    def test_travel_time_reuses_cached_distance_when_speed_is_known(self):
        model = _CountingTravelModel({
            ("A", "B"): 100.0,
        }, speed=10.0)
        bdm = BatchDistanceMatrix(model)
        bdm.precompute(["A", "B"])
        model.calls.clear()

        self.assertAlmostEqual(bdm.travel_time("A", "B"), 10.0)
        self.assertEqual(model.calls, [])

    def test_precompute_deduplicates(self):
        bdm = BatchDistanceMatrix(self.model)
        bdm.precompute(["A", "A", "B", "B"])
        self.assertEqual(bdm.distance("A", "B"), 100.0)

    def test_precompute_for_insertions_only_warms_needed_pairs(self):
        model = _CountingTravelModel({
            ("A", "B"): 1.0,
            ("B", "C"): 1.0,
            ("A", "P"): 1.0,
            ("P", "B"): 1.0,
            ("B", "P"): 1.0,
            ("P", "C"): 1.0,
        })
        courier = Courier(
            courier_id="c1",
            current_location="A",
            depot_location="C",
            capacity=10.0,
            current_load=0.0,
            route_locations=["B"],
            available_from=0,
        )
        parcel = Parcel(
            parcel_id="p1",
            location="P",
            arrival_time=0,
            deadline=100,
            weight=1.0,
            fare=10.0,
        )
        bdm = BatchDistanceMatrix(model)

        bdm.precompute_for_insertions([courier], [parcel])

        self.assertEqual(
            set(model.calls),
            {
                ("A", "B"),
                ("B", "C"),
                ("A", "P"),
                ("P", "B"),
                ("B", "P"),
                ("P", "C"),
            },
        )
        self.assertEqual(len(model.calls), 6)

    def test_batch_cache_reduces_repeated_insertion_distance_queries(self):
        model = _CountingTravelModel({
            ("A", "B"): 1.0,
            ("B", "C"): 1.0,
            ("A", "P"): 1.0,
            ("P", "B"): 1.0,
            ("B", "P"): 1.0,
            ("P", "C"): 1.0,
        })
        courier = Courier(
            courier_id="c1",
            current_location="A",
            depot_location="C",
            capacity=10.0,
            current_load=0.0,
            route_locations=["B"],
            available_from=0,
        )
        parcel = Parcel(
            parcel_id="p1",
            location="P",
            arrival_time=0,
            deadline=100,
            weight=1.0,
            fare=10.0,
        )

        find_best_local_insertion(parcel, courier, model)
        uncached_calls = len(model.calls)

        model.calls.clear()
        bdm = BatchDistanceMatrix(model)
        bdm.precompute_for_insertions([courier], [parcel])
        warmup_calls = len(model.calls)
        model.calls.clear()
        find_best_local_insertion(parcel, courier, bdm)
        cached_calls = len(model.calls)

        self.assertEqual(uncached_calls, 6)
        self.assertEqual(warmup_calls, 6)
        self.assertEqual(cached_calls, 0)


if __name__ == "__main__":
    unittest.main()
