"""Tests for the legacy-environment-backed Chengdu CAPA runner."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from capa import CAPAConfig, DistanceMatrixTravelModel, Parcel
from capa.models import CooperatingPlatform


class FakeTask:
    """Minimal legacy task stub for Chengdu runner tests."""

    def __init__(self, num: str, node: str, s_time: int, d_time: int, weight: float, fare: float) -> None:
        """Store the task attributes required by the adapter layer."""
        self.num = num
        self.l_node = node
        self.s_time = s_time
        self.d_time = d_time
        self.weight = weight
        self.fare = fare


class FakeStation:
    """Minimal station stub exposing the destination node expected by legacy couriers."""

    def __init__(self, num: int, node: str) -> None:
        """Persist the station identifier and node."""
        self.num = num
        self.l_node = node


class FakeLegacyCourier:
    """Minimal legacy courier stub compatible with the adapter tests."""

    def __init__(self, num: int, location: str, station: FakeStation, schedule=None, load: float = 0.0) -> None:
        """Populate the legacy courier fields read by the Chengdu adapter layer."""
        self.num = num
        self.location = location
        self.station = station
        self.station_num = station.num
        self.re_schedule = list(schedule or [])
        self.re_weight = load
        self.max_weight = 10.0
        self.sum_useful_time = 1000.0
        self.batch_take = 0
        self.service_score = 0.9
        self.w = 0.4
        self.c = 0.6
        self._deliver_after = {}


class ChengduRunnerTests(unittest.TestCase):
    """Validate the legacy-environment adapters and runner integration."""

    def setUp(self) -> None:
        """Create deterministic fixtures shared by the Chengdu runner tests."""
        self.travel = DistanceMatrixTravelModel(
            distances={
                ("L0", "T1"): 2.0,
                ("L0", "T2"): 8.0,
                ("T1", "S"): 2.0,
                ("T2", "S"): 6.0,
                ("L0", "S"): 4.0,
                ("P0", "T2"): 2.0,
                ("P0", "T1"): 8.0,
                ("T2", "PS"): 2.0,
                ("T1", "PS"): 6.0,
                ("P0", "PS"): 4.0,
            },
            speed=1.0,
        )
        self.config = CAPAConfig(
            batch_size=60,
            utility_balance_gamma=0.5,
            threshold_omega=1.0,
            local_payment_ratio_zeta=0.2,
            local_sharing_rate_mu1=0.5,
            cross_platform_sharing_rate_mu2=0.4,
        )

    def test_legacy_courier_snapshot_preserves_route_state(self) -> None:
        """Legacy couriers should convert into CAPA couriers without losing route semantics."""
        from env.chengdu import legacy_courier_to_capa

        station = FakeStation(1, "S")
        courier = FakeLegacyCourier(
            num=7,
            location="L0",
            station=station,
            schedule=[FakeTask("seed", "T1", 0, 100, 1.0, 0.0)],
            load=3.0,
        )

        snapshot = legacy_courier_to_capa(courier, courier_id="local-7")

        self.assertEqual(snapshot.courier_id, "local-7")
        self.assertEqual(snapshot.current_location, "L0")
        self.assertEqual(snapshot.depot_location, "S")
        self.assertEqual(snapshot.route_locations, ["T1"])
        self.assertEqual(snapshot.current_load, 3.0)
        self.assertEqual(snapshot.capacity, 10.0)

    def test_apply_assignment_to_legacy_courier_inserts_into_schedule(self) -> None:
        """Accepted assignments should be written back into the legacy route buffer."""
        from env.chengdu import apply_assignment_to_legacy_courier

        station = FakeStation(1, "S")
        seed_task = FakeTask("seed", "T1", 0, 100, 1.0, 0.0)
        new_task = FakeTask("new", "T2", 0, 100, 2.0, 8.0)
        courier = FakeLegacyCourier(num=7, location="L0", station=station, schedule=[seed_task], load=1.0)

        apply_assignment_to_legacy_courier(new_task, courier, insertion_index=0)

        self.assertEqual([task.num for task in courier.re_schedule], ["new", "seed"])
        self.assertEqual(courier.re_weight, 3.0)
        self.assertEqual(courier.batch_take, 1)

    def test_limit_legacy_tasks_trims_pick_and_delivery_inputs(self) -> None:
        """Preprocessing should only keep the task volume required by the requested experiment size."""
        from env.chengdu import limit_legacy_tasks

        pick_tasks = [FakeTask(f"p{i}", f"N{i}", i, i + 100, 1.0, 10.0) for i in range(10)]
        delivery_tasks = [FakeTask(f"d{i}", f"M{i}", i, i + 100, 1.0, 0.0) for i in range(10)]

        limited_pick, limited_delivery = limit_legacy_tasks(
            pick_tasks=pick_tasks,
            delivery_tasks=delivery_tasks,
            num_parcels=3,
            required_couriers=2,
        )

        self.assertEqual([task.num for task in limited_pick], ["p0", "p1", "p2"])
        self.assertEqual([task.num for task in limited_delivery], ["d0", "d1"])

    def test_iter_delivery_seed_counts_doubles_until_full_dataset(self) -> None:
        """Delivery seed expansion should grow geometrically until all candidates are exhausted."""
        from env.chengdu import iter_delivery_seed_counts

        self.assertEqual(list(iter_delivery_seed_counts(required_couriers=3, total_delivery_tasks=20)), [3, 6, 12, 20])

    def test_select_station_pick_tasks_uses_station_ranges(self) -> None:
        """Pick-task selection should follow the same station-range rule as the legacy framework."""
        from env.chengdu import select_station_pick_tasks

        station = FakeStation(1, "S")
        station.station_range = [0.0, 10.0, 0.0, 10.0]
        station.f_pick_task_set = []
        inside = FakeTask("p1", "N1", 0, 100, 1.0, 10.0)
        inside.l_lng = 5.0
        inside.l_lat = 5.0
        outside = FakeTask("p2", "N2", 0, 100, 1.0, 10.0)
        outside.l_lng = 15.0
        outside.l_lat = 15.0

        selected = select_station_pick_tasks([station], [inside, outside], num_parcels=1)

        self.assertEqual([task.num for task in selected], ["p1"])
        self.assertEqual([task.num for task in station.f_pick_task_set], ["p1"])

    def test_assign_delivery_tasks_to_stations_uses_station_ranges(self) -> None:
        """Delivery-task assignment should follow the same station-range rule as the legacy framework."""
        from env.chengdu import assign_delivery_tasks_to_stations

        station = FakeStation(1, "S")
        station.station_range = [0.0, 10.0, 0.0, 10.0]
        station.station_task_set = []
        inside = FakeTask("d1", "N1", 0, 100, 1.0, 0.0)
        inside.l_lng = 5.0
        inside.l_lat = 5.0
        outside = FakeTask("d2", "N2", 0, 100, 1.0, 0.0)
        outside.l_lng = 15.0
        outside.l_lat = 15.0

        assign_delivery_tasks_to_stations([station], [inside, outside])

        self.assertEqual([task.num for task in station.station_task_set], ["d1"])

    def test_time_stepped_runner_advances_couriers_and_reports_metrics(self) -> None:
        """The Chengdu runner should call the movement hook and emit aggregate metrics."""
        from env.chengdu import run_time_stepped_chengdu_batches

        local_station = FakeStation(1, "S")
        partner_station = FakeStation(2, "PS")
        local_courier = FakeLegacyCourier(num=1, location="L0", station=local_station)
        partner_courier = FakeLegacyCourier(num=2, location="P0", station=partner_station)
        partner_platform = CooperatingPlatform(
            platform_id="P1",
            couriers=[],
            base_price=1.0,
            sharing_rate_gamma=0.4,
            historical_quality=1.0,
        )
        tasks = [
            FakeTask("t1", "T1", 0, 30, 1.0, 10.0),
            FakeTask("t2", "T2", 0, 30, 1.0, 10.0),
        ]
        move_calls = []

        def movement_callback(local_couriers, partner_couriers, step_seconds, station_set) -> None:
            move_calls.append((len(local_couriers), len(partner_couriers), step_seconds, len(station_set)))
            for courier in [*local_couriers, *partner_couriers]:
                if not courier.re_schedule:
                    continue
                head = courier.re_schedule.pop(0)
                courier.location = head.l_node
                courier.re_weight -= head.weight

        result = run_time_stepped_chengdu_batches(
            tasks=tasks,
            local_couriers=[local_courier],
            partner_couriers_by_platform={"P1": [partner_courier]},
            station_set=[local_station, partner_station],
            travel_model=self.travel,
            config=self.config,
            batch_seconds=60,
            step_seconds=60,
            platform_base_prices={"P1": 1.0},
            platform_sharing_rates={"P1": 0.4},
            platform_qualities={"P1": 1.0},
            movement_callback=movement_callback,
        )

        self.assertGreaterEqual(len(move_calls), 1)
        self.assertEqual(len(result.matching_plan), 2)
        self.assertAlmostEqual(result.metrics.completion_rate, 1.0)
        self.assertGreaterEqual(result.metrics.total_revenue, 0.0)

    def test_time_stepped_runner_drains_routes_after_last_batch(self) -> None:
        """The runner should keep stepping after the final batch until accepted parcels are physically delivered."""
        from env.chengdu import run_time_stepped_chengdu_batches

        local_station = FakeStation(1, "S")
        local_courier = FakeLegacyCourier(num=1, location="L0", station=local_station)
        task = FakeTask("t1", "T1", 40, 100, 1.0, 10.0)
        move_calls = []

        def delayed_delivery_callback(local_couriers, partner_couriers, step_seconds, station_set) -> None:
            move_calls.append((len(local_couriers), len(partner_couriers), step_seconds, len(station_set)))
            for courier in [*local_couriers, *partner_couriers]:
                if not courier.re_schedule:
                    continue
                head = courier.re_schedule[0]
                remaining = courier._deliver_after.get(head.num, 2)
                remaining -= 1
                courier._deliver_after[head.num] = remaining
                if remaining <= 0:
                    courier.location = head.l_node
                    courier.re_weight -= head.weight
                    courier.re_schedule.pop(0)

        result = run_time_stepped_chengdu_batches(
            tasks=[task],
            local_couriers=[local_courier],
            partner_couriers_by_platform={},
            station_set=[local_station],
            travel_model=self.travel,
            config=self.config,
            batch_seconds=60,
            step_seconds=20,
            platform_base_prices={},
            platform_sharing_rates={},
            platform_qualities={},
            movement_callback=delayed_delivery_callback,
        )

        self.assertGreaterEqual(len(move_calls), 2)
        self.assertEqual(local_courier.re_schedule, [])
        self.assertEqual(result.metrics.delivered_parcel_count, 1)
        self.assertAlmostEqual(result.metrics.completion_rate, 1.0)

    def test_generate_origin_schedule_with_retry_skips_oversized_sample_requests(self) -> None:
        """The environment builder should retry when legacy schedule seeding requests more couriers than can be sampled."""
        from env.chengdu import generate_origin_schedule_with_retry

        attempts = []

        class FakeFramework:
            parameter_courier_num = 0

            @staticmethod
            def GenerateOriginSchedule(station_set, preference):
                attempts.append(FakeFramework.parameter_courier_num)
                if FakeFramework.parameter_courier_num > 2:
                    raise ValueError("Sample larger than population or is negative")
                return [SimpleNamespace(num=1), SimpleNamespace(num=2)]

        seeded = generate_origin_schedule_with_retry(
            framework=FakeFramework,
            station_set=[object()],
            required_couriers=3,
            candidate_seed_count=3,
            preference=0.5,
        )

        self.assertEqual(len(seeded), 2)
        self.assertEqual(attempts, [3, 2])


if __name__ == "__main__":
    unittest.main()
