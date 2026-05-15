"""Tests for paper plot filtering and labels."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from experiments import plotting


def test_bpt_label_uses_batch_process_time() -> None:
    """BPT should expand to batch process time in plots."""

    assert plotting.METRIC_LABEL["BPT"] == "Batch Process Time"


def test_comparison_plot_filters_basegta_and_bpt_mra() -> None:
    """Comparison plots should hide BaseGTA everywhere and MRA on BPT."""

    summary = {
        "sweep_parameter": "num_parcels",
        "algorithms": ["capa", "greedy", "basegta", "impgta", "mra", "ramcom"],
        "runs": [
            {
                "num_parcels": 100,
                **{
                    algorithm: {"metrics": {"TR": 1.0, "CR": 0.5, "BPT": 0.1}}
                    for algorithm in ["capa", "greedy", "basegta", "impgta", "mra", "ramcom"]
                },
            }
        ],
    }
    captured: dict[str, list[str]] = {}

    def fake_save_line_plot(*, series, metric_name, **_kwargs):
        captured[metric_name] = [algorithm for algorithm, _values in series]

    with patch("experiments.plotting._save_line_plot", side_effect=fake_save_line_plot):
        plotting.save_comparison_plots(summary, Path("/tmp/plot-filter-test"))

    assert captured["TR"] == ["capa", "greedy", "impgta", "mra", "ramcom"]
    assert captured["CR"] == ["capa", "greedy", "impgta", "mra", "ramcom"]
    assert captured["BPT"] == ["capa", "greedy", "impgta", "ramcom"]


def test_visible_algorithms_for_metric_applies_default_comparison_filter() -> None:
    """Default comparison plots should use the same metric-specific filtering."""

    algorithms = ["capa", "greedy", "basegta", "impgta", "mra", "ramcom"]

    assert plotting.visible_algorithms_for_metric("TR", algorithms) == ["capa", "greedy", "impgta", "mra", "ramcom"]
    assert plotting.visible_algorithms_for_metric("CR", algorithms) == ["capa", "greedy", "impgta", "mra", "ramcom"]
    assert plotting.visible_algorithms_for_metric("BPT", algorithms) == ["capa", "greedy", "impgta", "ramcom"]
