"""Tests for paper plot filtering and labels."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from experiments import plotting


def test_bpt_label_uses_batch_process_time() -> None:
    """BPT should expand to batch process time in plots."""

    assert plotting.METRIC_LABEL["BPT"] == "Batch Process Time"


def test_num_parcels_label_uses_gamma_symbol() -> None:
    """Parcel-count plots should use the paper's Gamma parcel-set symbol."""

    assert plotting.XLABEL_OVERRIDE["num_parcels"] == r"Number of Parcels $|\Gamma|$"
    assert "|P|" not in plotting.XLABEL_OVERRIDE["num_parcels"]


def test_plot_rc_uses_times_new_roman_as_primary_font() -> None:
    """Plot text should request Times New Roman before fallback fonts."""

    import matplotlib.pyplot as plt

    plotting._apply_rc()

    assert plt.rcParams["font.family"][0] == "Times New Roman"


def test_line_plot_uses_numeric_x_spacing_and_scientific_x_axis(tmp_path: Path) -> None:
    """Numeric sweep coordinates should scale by the smallest coordinate exponent."""

    import matplotlib.pyplot as plt

    output_path = tmp_path / "plot.png"

    with patch("matplotlib.figure.Figure.savefig"), patch("matplotlib.pyplot.close"):
        plotting._save_line_plot(
            x_values=[1000, 2000, 5000, 10000, 20000],
            series=[("capa", [1.0, 2.0, 3.0, 4.0, 5.0])],
            x_label="num_parcels",
            metric_name="TR",
            output_path=output_path,
        )
        ax = plt.gcf().axes[0]

    assert list(ax.lines[0].get_xdata()) == [1.0, 2.0, 5.0, 10.0, 20.0]
    assert [tick.get_text() for tick in ax.get_xticklabels()] == ["1", "2", "5", "10", "20"]
    assert ax.xaxis.get_major_formatter().get_offset() == r"$\times10^{3}$"
    assert ax.get_xscale() == "linear"
    assert ax.get_xlim() == (1.0, 20.0)
    assert all(label.get_rotation() == 0 for label in ax.get_xticklabels())
    assert all(label.get_fontsize() == 18 for label in ax.get_xticklabels())


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
