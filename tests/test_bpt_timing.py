"""Tests for assignment-only BPT timing semantics."""

from __future__ import annotations

import unittest

from capa.metrics import build_run_metrics, compute_batch_processing_time
from capa.models import BatchReport, Parcel


class BPTTimingTests(unittest.TestCase):
    """Verify that reported BPT excludes routing, insertion, and movement overhead."""

    def test_compute_batch_processing_time_uses_decision_time_only(self) -> None:
        """Aggregate BPT should sum decision-time fields instead of full wall-clock work."""
        from experiments.timing import BatchTimingBreakdown

        reports = [
            BatchReport(
                batch_index=1,
                batch_time=0,
                input_parcels=[],
                local_assignments=[],
                cross_assignments=[],
                unresolved_parcels=[],
                processing_time_seconds=9.0,
                timing=BatchTimingBreakdown(
                    decision_time_seconds=1.5,
                    routing_time_seconds=2.0,
                    insertion_time_seconds=3.0,
                    movement_time_seconds=2.5,
                ),
            ),
            BatchReport(
                batch_index=2,
                batch_time=15,
                input_parcels=[],
                local_assignments=[],
                cross_assignments=[],
                unresolved_parcels=[],
                processing_time_seconds=7.0,
                timing=BatchTimingBreakdown(
                    decision_time_seconds=0.5,
                    routing_time_seconds=1.0,
                    insertion_time_seconds=2.0,
                    movement_time_seconds=3.5,
                ),
            ),
        ]

        self.assertEqual(compute_batch_processing_time(reports), 2.0)

    def test_build_run_metrics_preserves_excluded_timing_breakdown(self) -> None:
        """Run metrics should expose the excluded timing counters without folding them into BPT."""
        from experiments.timing import BatchTimingBreakdown

        report = BatchReport(
            batch_index=1,
            batch_time=0,
            input_parcels=[
                Parcel(parcel_id="p1", location="L1", arrival_time=0, deadline=10, weight=1.0, fare=5.0),
            ],
            local_assignments=[],
            cross_assignments=[],
            unresolved_parcels=[],
            processing_time_seconds=4.0,
            timing=BatchTimingBreakdown(
                decision_time_seconds=0.25,
                routing_time_seconds=1.25,
                insertion_time_seconds=1.5,
                movement_time_seconds=1.0,
            ),
        )

        metrics = build_run_metrics(assignments=[], total_parcels=1, batch_reports=[report], delivered_parcel_count=0)

        self.assertEqual(metrics.batch_processing_time, 0.25)
        self.assertEqual(metrics.excluded_routing_time, 1.25)
        self.assertEqual(metrics.excluded_insertion_time, 1.5)
        self.assertEqual(metrics.excluded_movement_time, 1.0)


if __name__ == "__main__":
    unittest.main()
