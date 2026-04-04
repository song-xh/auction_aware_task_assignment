"""Tests for geometric pre-filtering and batch distance matrix."""

from __future__ import annotations

import unittest

from capa.batch_distance import BatchDistanceMatrix
from capa.constraints import is_deadline_feasible_by_geo, is_within_service_radius
from capa.geo import GeoIndex, haversine_meters


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

    def test_fallback_on_miss(self):
        bdm = BatchDistanceMatrix(self.model)
        bdm.precompute(["A"])  # only self-distance
        # "A","B" not precomputed but should fall through
        self.assertEqual(bdm.distance("A", "B"), 100.0)

    def test_travel_time_delegates(self):
        bdm = BatchDistanceMatrix(self.model)
        self.assertAlmostEqual(bdm.travel_time("A", "B"), 10.0)

    def test_precompute_deduplicates(self):
        bdm = BatchDistanceMatrix(self.model)
        bdm.precompute(["A", "A", "B", "B"])
        self.assertEqual(bdm.distance("A", "B"), 100.0)


if __name__ == "__main__":
    unittest.main()
