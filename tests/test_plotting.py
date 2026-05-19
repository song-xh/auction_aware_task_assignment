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

    assert plotting.XLABEL_OVERRIDE["num_parcels"] == r"Number of Parcels $\Gamma$"
    assert r"\mathcal{P}" not in plotting.XLABEL_OVERRIDE["num_parcels"]


def test_all_sweep_labels_use_math_notation_symbols() -> None:
    """Sweep labels should use math notation for the paper symbols."""

    assert plotting.XLABEL_OVERRIDE["local_couriers"] == r"Number of Local Couriers $\mathcal{C}$"
    assert plotting.XLABEL_OVERRIDE["service_radius"] == r"Service Radius $r$ (km)"
    assert plotting.XLABEL_OVERRIDE["platforms"] == r"Number of Platforms $\mathcal{P}$"
    assert plotting.XLABEL_OVERRIDE["courier_capacity"] == r"Courier Capacity $\kappa$"


def test_default_comparison_figure_size_is_more_compact() -> None:
    """Default comparison plots should use a tighter figure size than 6x5."""

    assert plotting.DEFAULT_COMPARISON_FIGSIZE == (5.4, 4.4)


def test_plot_rc_uses_times_new_roman_as_primary_font() -> None:
    """Plot text should request Times New Roman before fallback fonts."""

    import matplotlib.pyplot as plt

    plotting._apply_rc()

    assert plt.rcParams["font.family"][0] == "Times New Roman"
    assert plt.rcParams["mathtext.it"] == "serif"


def test_line_plot_uses_numeric_x_spacing_and_scientific_x_axis(tmp_path: Path) -> None:
    """Numeric sweep coordinates should use uniform spacing with scientific labels."""

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

    assert list(ax.lines[0].get_xdata()) == [0, 1, 2, 3, 4]
    assert [tick.get_text() for tick in ax.get_xticklabels()] == ["1", "2", "5", "10", "20"]
    assert ax.get_xscale() == "linear"
    assert ax.get_xlim() == (0.0, 4.0)
    assert all(label.get_rotation() == 0 for label in ax.get_xticklabels())
    assert all(label.get_fontsize() == 18 for label in ax.get_xticklabels())
    assert ax.xaxis.get_offset_text().get_text() == ""
    assert ax.get_xlabel() == r"Number of Parcels $\Gamma$ ($\times10^{3}$)"


def test_scale_by_smallest_scientific_exponent_uses_minimum_nonzero_order() -> None:
    """Scaled x-axis values should factor out the smallest nonzero magnitude."""

    scaled, exponent = plotting._scale_by_smallest_scientific_exponent([10, 1000, 10000])

    assert scaled == [1.0, 100.0, 1000.0]
    assert exponent == 1


def test_scale_by_smallest_scientific_exponent_keeps_integer_mantissas() -> None:
    """Shared scaling should prefer an integer mantissa over decimal notation."""

    scaled, exponent = plotting._scale_by_smallest_scientific_exponent([1000, 2200, 5000])

    assert scaled == [10.0, 22.0, 50.0]
    assert exponent == 2


def test_apply_scientific_y_formatter_uses_integer_mantissas() -> None:
    """Scientific y-axis labels should be integer mantissas with one shared exponent."""

    import matplotlib.pyplot as plt

    figure, ax = plt.subplots()
    ax.set_yticks([0, 2200, 4400])

    exponent = plotting._apply_scientific_y_formatter(ax)

    assert [tick.get_text() for tick in ax.get_yticklabels()] == ["0", "22", "44"]
    assert exponent == 2
    assert ax.yaxis.get_offset_text().get_text() == ""
    plt.close(figure)


def test_axis_label_with_exponent_appends_shared_multiplier() -> None:
    """Axis labels should carry the shared scientific multiplier beside the title."""

    assert plotting._axis_label_with_exponent("Total Revenue", 0) == "Total Revenue"
    assert plotting._axis_label_with_exponent("Total Revenue", 3) == r"Total Revenue ($\times10^{3}$)"


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


def test_visible_algorithms_for_bar_hides_basegta_in_exp4() -> None:
    """Platform bar plots should omit BaseGTA alongside the low-performing baselines."""

    algorithms = ["capa", "greedy", "basegta", "impgta", "mra", "ramcom", "rlcapa"]

    assert plotting.visible_algorithms_for_bar("TR", algorithms) == ["capa", "impgta", "ramcom", "rlcapa"]
    assert plotting.visible_algorithms_for_bar("CR", algorithms) == ["capa", "impgta", "ramcom", "rlcapa"]
    assert plotting.visible_algorithms_for_bar("BPT", algorithms) == ["capa", "impgta", "ramcom", "rlcapa"]


def test_grouped_bar_plot_uses_hatches_and_patch_legend(tmp_path: Path) -> None:
    """Platform bar plots should use hatched bars and an in-plot patch legend."""

    import matplotlib.pyplot as plt

    output_path = tmp_path / "bar.png"

    with patch("matplotlib.figure.Figure.savefig"), patch("matplotlib.pyplot.close"):
        plotting._save_grouped_bar_plot(
            x_values=[2, 4, 8],
            series=[
                ("capa", [1.0, 2.0, 3.0]),
                ("impgta", [1.5, 2.5, 3.5]),
                ("ramcom", [0.5, 1.5, 2.5]),
                ("rlcapa", [2.0, 3.0, 4.0]),
            ],
            x_label="platforms",
            metric_name="TR",
            output_path=output_path,
        )
        ax = plt.gcf().axes[0]

    legend = ax.get_legend()

    assert legend is not None
    assert [text.get_text() for text in legend.get_texts()] == [
        "CAPA",
        "ImpGTA",
        "RAMCOM",
        "RL-CAPA",
    ]
    assert ax.patches[0].get_hatch() == plotting.BAR_STYLE["capa"]["hatch"]
    assert ax.patches[3].get_hatch() == plotting.BAR_STYLE["impgta"]["hatch"]
    assert [round(float(value), 2) for value in ax.get_xticks()] == [0.0, 0.7, 1.4]
    assert tuple(round(float(value), 2) for value in ax.get_xlim()) == (-0.42, 1.82)


def test_line_plot_formats_cr_axis_as_integer_percent(tmp_path: Path) -> None:
    """CR plots should render percentage labels with integer ticks."""

    import matplotlib.pyplot as plt

    output_path = tmp_path / "cr.png"

    with patch("matplotlib.figure.Figure.savefig"), patch("matplotlib.pyplot.close"):
        plotting._save_line_plot(
            x_values=[100, 200, 300],
            series=[("capa", [0.445, 0.4862, 0.5224])],
            x_label="local_couriers",
            metric_name="CR",
            output_path=output_path,
        )
        ax = plt.gcf().axes[0]

    labels = [tick.get_text() for tick in ax.get_yticklabels() if tick.get_text()]

    assert ax.get_ylabel() == "Completion Rate (%)"
    assert 1 <= len(labels) <= 5
    assert all("." not in label for label in labels)


def test_line_plot_formats_bpt_axis_in_ms(tmp_path: Path) -> None:
    """BPT plots should use milliseconds on the y-axis."""

    import matplotlib.pyplot as plt

    output_path = tmp_path / "bpt.png"

    with patch("matplotlib.figure.Figure.savefig"), patch("matplotlib.pyplot.close"):
        plotting._save_line_plot(
            x_values=[500, 2000, 5000],
            series=[("capa", [0.227748, 0.218733, 0.232102])],
            x_label="num_parcels",
            metric_name="BPT",
            output_path=output_path,
        )
        ax = plt.gcf().axes[0]

    assert ax.get_ylabel().startswith("BPT")
    assert "ms" in ax.get_ylabel()


def test_exp1_tr_plot_uses_log10_y_axis_label(tmp_path: Path) -> None:
    """Exp-1 TR plots should compress revenue with a log10 y-axis."""

    import matplotlib.pyplot as plt

    output_path = tmp_path / "tr.png"

    with patch("matplotlib.figure.Figure.savefig"), patch("matplotlib.pyplot.close"):
        plotting._save_line_plot(
            x_values=[500, 2000, 5000, 10000, 20000],
            series=[("capa", [1317.54, 5736.95, 14624.23, 27560.34, 48965.33])],
            x_label="num_parcels",
            metric_name="TR",
            output_path=output_path,
        )
        ax = plt.gcf().axes[0]

    assert ax.get_ylabel() == r"Total Revenue ($\log_{10}$)"


def test_line_plot_legend_uses_framed_non_center_location(tmp_path: Path) -> None:
    """Legends should avoid centered placement and use a visible frame."""

    import matplotlib.pyplot as plt

    output_path = tmp_path / "legend.png"

    with patch("matplotlib.figure.Figure.savefig"), patch("matplotlib.pyplot.close"):
        plotting._save_line_plot(
            x_values=[500, 2000, 5000],
            series=[
                ("capa", [1.0, 2.0, 3.0]),
                ("greedy", [0.5, 1.0, 1.5]),
                ("impgta", [1.2, 2.2, 3.2]),
            ],
            x_label="num_parcels",
            metric_name="TR",
            output_path=output_path,
        )
        ax = plt.gcf().axes[0]

    legend = ax.get_legend()

    assert legend is not None
    assert legend.get_frame_on() is True
    assert legend._loc != 0


def test_exp1_tr_plot_uses_integer_log_ticks_2_3_4(tmp_path: Path) -> None:
    """Exp-1 TR should show at least the integer log ticks 2, 3, and 4."""

    import matplotlib.pyplot as plt

    output_path = tmp_path / "exp1-tr.png"

    with patch("matplotlib.figure.Figure.savefig"), patch("matplotlib.pyplot.close"):
        plotting._save_line_plot(
            x_values=[500, 2000, 5000, 10000, 20000],
            series=[
                ("capa", [1317.54, 5736.95, 14624.23, 27560.34, 48965.33]),
                ("greedy", [362.45, 2418.85, 7281.19, 12066.23, 14760.35]),
            ],
            x_label="num_parcels",
            metric_name="TR",
            output_path=output_path,
        )
        ax = plt.gcf().axes[0]

    labels = [tick.get_text() for tick in ax.get_yticklabels()]

    assert "2" in labels
    assert "3" in labels
    assert "4" in labels


def test_exp2_tr_plot_limits_y_ticks_to_five_or_fewer(tmp_path: Path) -> None:
    """Exp-2 TR should not render an excessive y-tick count."""

    import matplotlib.pyplot as plt

    output_path = tmp_path / "exp2-tr.png"

    with patch("matplotlib.figure.Figure.savefig"), patch("matplotlib.pyplot.close"):
        plotting._save_line_plot(
            x_values=[100, 200, 300, 400, 500],
            series=[
                ("capa", [10238.03, 11120.70, 11453.88, 11871.22, 11729.52]),
                ("impgta", [13794.39, 13841.65, 14299.24, 14061.35, 13969.21]),
            ],
            x_label="local_couriers",
            metric_name="TR",
            output_path=output_path,
        )
        ax = plt.gcf().axes[0]

    labels = [tick.get_text() for tick in ax.get_yticklabels() if tick.get_text()]

    assert len(labels) <= 5


def test_exp4_bar_plot_uses_two_column_upper_left_legend(tmp_path: Path) -> None:
    """Exp-4 legend should be a compact 2x2 block in the upper-left corner."""

    import matplotlib.pyplot as plt

    output_path = tmp_path / "exp4-bar.png"

    with patch("matplotlib.figure.Figure.savefig"), patch("matplotlib.pyplot.close"):
        plotting._save_grouped_bar_plot(
            x_values=[2, 4, 8, 12, 16],
            series=[
                ("capa", [1.0, 2.0, 3.0, 4.0, 5.0]),
                ("impgta", [1.5, 2.5, 3.5, 4.5, 5.5]),
                ("ramcom", [0.5, 1.5, 2.5, 3.5, 4.5]),
                ("rlcapa", [2.0, 3.0, 4.0, 5.0, 6.0]),
            ],
            x_label="platforms",
            metric_name="TR",
            output_path=output_path,
        )
        ax = plt.gcf().axes[0]

    legend = ax.get_legend()

    assert legend is not None
    assert legend._ncols == 2
    assert legend._loc == 2
