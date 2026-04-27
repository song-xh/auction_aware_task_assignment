"""Tests for Chengdu paper-style sweep presets and fixed defaults."""

from __future__ import annotations

from experiments.paper_chengdu import DEFAULT_CHENGDU_PAPER_FIXED_CONFIG
from experiments.paper_config import PAPER_SUITE_PRESETS


def test_formal_paper_presets_match_requested_experiment_points() -> None:
    """The formal Chengdu sweep presets should expose the requested axis points."""

    formal = PAPER_SUITE_PRESETS["chengdu-paper"]["formal"]

    assert formal["num_parcels"] == [1000, 2000, 5000, 10000, 20000]
    assert formal["local_couriers"] == [100, 200, 300, 400, 500]
    assert formal["service_radius"] == [0.5, 1.0, 1.5, 2.0, 2.5]
    assert formal["platforms"] == [2, 4, 8, 12, 16]
    assert formal["courier_capacity"] == [25, 50, 75, 100, 125]


def test_default_fixed_config_uses_new_cross_experiment_baselines() -> None:
    """The shared fixed Chengdu config should use the requested default points."""

    assert DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["num_parcels"] == 5000
    assert DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["local_couriers"] == 200
    assert DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["platforms"] == 4
    assert DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["courier_capacity"] == 50.0
