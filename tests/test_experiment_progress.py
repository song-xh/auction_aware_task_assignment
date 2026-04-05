"""Tests for Exp-1 terminal progress rendering helpers."""

from __future__ import annotations

import unittest


class ExperimentProgressTests(unittest.TestCase):
    """Verify live progress-bar formatting for split Exp-1 runs."""

    def test_render_progress_bar_uses_completed_fraction(self) -> None:
        """The bar renderer should convert a completed fraction into a bounded ASCII bar."""
        from experiments.progress import render_progress_bar

        rendered = render_progress_bar(completed=3.0, total=12.0, width=12)

        self.assertIn("[", rendered)
        self.assertIn("]", rendered)
        self.assertIn("25.0%", rendered)

    def test_format_split_progress_snapshot_includes_bar_and_active_details(self) -> None:
        """Formatted terminal output should show stage, active point details, and the overall bar."""
        from experiments.progress import format_split_progress_snapshot

        snapshot = {
            "state": "running",
            "completed_points": 0,
            "total_points": 4,
            "completed_algorithm_units": 3.5,
            "total_algorithm_units": 24,
            "algorithms_per_point": 6,
            "points": {
                "1000": {
                    "completed_algorithms": ["capa"],
                    "current_algorithm": "greedy",
                    "algorithm_index": 2,
                    "total_algorithms": 6,
                    "point_complete": False,
                    "last_event": {
                        "phase": "dispatch",
                        "detail": "task 15/100",
                        "completed_units": 15,
                        "total_units": 100,
                    },
                },
            },
        }

        rendered = format_split_progress_snapshot(snapshot)

        self.assertIn("state=running", rendered)
        self.assertIn("|Γ|=1000", rendered)
        self.assertIn("algo=2/6:greedy", rendered)
        self.assertIn("task 15/100", rendered)
        self.assertIn("Overall", rendered)
        self.assertIn("algorithm_runs=3.50/24", rendered)

    def test_render_terminal_progress_block_can_clear_previous_output(self) -> None:
        """Terminal rendering should support ANSI overwrite mode for live refreshes."""
        from experiments.progress import render_terminal_progress_block

        rendered = render_terminal_progress_block("hello", overwrite=True)

        self.assertTrue(rendered.startswith("\x1b[2J\x1b[H"))
        self.assertTrue(rendered.endswith("hello"))
