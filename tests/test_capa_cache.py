"""Tests for cache primitives used by the Chengdu-backed CAPA hot paths."""

import unittest

from capa import Courier, Parcel
from capa.utility import find_best_local_insertion
from tests.test_chengdu_runner import FakeLegacyCourier, FakeStation, FakeTask


class CountingTravelModel:
    """Minimal travel model that counts distance calls for cache tests."""

    def __init__(self, distances: dict[tuple[str, str], float]) -> None:
        """Store deterministic distances and initialize counters."""
        self._distances = distances
        self.distance_calls = 0

    def distance(self, start: str, end: str) -> float:
        """Return the deterministic distance and count the lookup."""
        self.distance_calls += 1
        if start == end:
            return 0.0
        if (start, end) in self._distances:
            return self._distances[(start, end)]
        if (end, start) in self._distances:
            return self._distances[(end, start)]
        raise KeyError((start, end))

    def travel_time(self, start: str, end: str) -> float:
        """Mirror distance so the test object satisfies the travel-model interface."""
        return self.distance(start, end)


class CAPACacheTests(unittest.TestCase):
    """Validate the new cache layer before it is wired into the hot paths."""

    def test_insertion_cache_reuses_best_local_insertion_result(self) -> None:
        """Repeated insertion checks on the same courier route should reuse the cached result."""
        from capa.cache import InsertionCache

        travel_model = CountingTravelModel(
            distances={
                ("S", "A"): 2.0,
                ("A", "D"): 2.0,
                ("S", "D"): 4.0,
            }
        )
        courier = Courier(
            courier_id="c1",
            current_location="S",
            depot_location="D",
            capacity=10.0,
            current_load=0.0,
        )
        parcel = Parcel("p1", "A", 0, 10, 1.0, 8.0)
        cache = InsertionCache()

        first = find_best_local_insertion(parcel, courier, travel_model, insertion_cache=cache)
        calls_after_first = travel_model.distance_calls
        second = find_best_local_insertion(parcel, courier, travel_model, insertion_cache=cache)

        self.assertEqual(first, second)
        self.assertEqual(travel_model.distance_calls, calls_after_first)

    def test_legacy_snapshot_cache_reuses_snapshot_until_state_changes(self) -> None:
        """Legacy courier projection should be reused until the legacy route state changes."""
        from env.chengdu import LegacyCourierSnapshotCache

        station = FakeStation(1, "S")
        courier = FakeLegacyCourier(
            num=1,
            location="L0",
            station=station,
            schedule=[FakeTask("seed", "A", 0, 100, 1.0, 0.0)],
            load=1.0,
        )
        cache = LegacyCourierSnapshotCache()

        first = cache.get(courier, courier_id="local-1")
        second = cache.get(courier, courier_id="local-1")
        courier.location = "A"
        third = cache.get(courier, courier_id="local-1")

        self.assertIs(first, second)
        self.assertIsNot(first, third)
        self.assertEqual(third.current_location, "A")


if __name__ == "__main__":
    unittest.main()
