"""Tests for unified experiment plotting outputs."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from experiments.plotting import save_comparison_plots, save_single_algorithm_plots


class ExperimentPlottingTests(unittest.TestCase):
    """Verify that sweep and comparison summaries emit the expected plots."""

    def test_save_single_algorithm_plots_writes_three_metric_figures(self) -> None:
        """Single-algorithm sweep summaries should produce TR, CR, and BPT plots."""
        summary = {
            "sweep_parameter": "num_parcels",
            "algorithm": "capa",
            "runs": [
                {"num_parcels": 10, "capa": {"metrics": {"TR": 1.0, "CR": 0.5, "BPT": 0.1}}},
                {"num_parcels": 20, "capa": {"metrics": {"TR": 2.0, "CR": 0.6, "BPT": 0.2}}},
            ],
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            save_single_algorithm_plots(summary=summary, output_dir=output_dir)
            self.assertTrue((output_dir / "tr_vs_num_parcels.png").exists())
            self.assertTrue((output_dir / "cr_vs_num_parcels.png").exists())
            self.assertTrue((output_dir / "bpt_vs_num_parcels.png").exists())

    def test_save_comparison_plots_writes_three_metric_figures(self) -> None:
        """Comparison summaries should produce multi-algorithm TR, CR, and BPT plots."""
        summary = {
            "sweep_parameter": "num_parcels",
            "algorithms": ["capa", "greedy"],
            "runs": [
                {
                    "num_parcels": 10,
                    "capa": {"metrics": {"TR": 1.0, "CR": 0.5, "BPT": 0.1}},
                    "greedy": {"metrics": {"TR": 0.8, "CR": 0.4, "BPT": 0.05}},
                },
                {
                    "num_parcels": 20,
                    "capa": {"metrics": {"TR": 2.0, "CR": 0.6, "BPT": 0.2}},
                    "greedy": {"metrics": {"TR": 1.2, "CR": 0.45, "BPT": 0.07}},
                },
            ],
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            save_comparison_plots(summary=summary, output_dir=output_dir)
            self.assertTrue((output_dir / "tr_vs_num_parcels.png").exists())
            self.assertTrue((output_dir / "cr_vs_num_parcels.png").exists())
            self.assertTrue((output_dir / "bpt_vs_num_parcels.png").exists())
