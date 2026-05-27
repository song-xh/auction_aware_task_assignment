"""Tests for Chengdu paper-style sweep presets and fixed defaults."""

from __future__ import annotations

from experiments.paper_chengdu import (
    DEFAULT_CHENGDU_PAPER_FIXED_CONFIG,
    build_fixed_config_from_args,
    build_script_parser,
)
from experiments.paper_config import DEFAULT_CHENGDU_PAPER_ALGORITHMS, PAPER_SUITE_PRESETS


def test_formal_paper_presets_match_requested_experiment_points() -> None:
    """The formal Chengdu sweep presets should expose the requested axis points."""

    formal = PAPER_SUITE_PRESETS["chengdu-paper"]["formal"]

    assert formal["num_parcels"] == [5000, 20000, 50000, 100000, 200000]
    assert formal["local_couriers"] == [1000, 2000, 3000, 4000, 5000]
    assert formal["service_radius"] == [0.5, 1.0, 1.5, 2.0, 2.5]
    assert formal["platforms"] == [2, 4, 8, 12, 16]
    assert formal["courier_capacity"] == [25, 50, 75, 100, 125]


def test_default_fixed_config_uses_new_cross_experiment_baselines() -> None:
    """The shared fixed Chengdu config should use the requested default points."""

    assert DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["num_parcels"] == 50000
    assert DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["local_couriers"] == 3000
    assert DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["platforms"] == 4
    assert DEFAULT_CHENGDU_PAPER_FIXED_CONFIG["courier_capacity"] == 50.0


def test_formal_and_ny_resolve_preset_specific_exp1_background_defaults() -> None:
    """Preset parsing should preserve each Exp-1 fixed background environment."""

    parser = build_script_parser("test")
    formal = build_fixed_config_from_args(
        parser.parse_args(["--output-dir", "/tmp/formal", "--preset", "formal"])
    )
    ny = build_fixed_config_from_args(
        parser.parse_args(["--output-dir", "/tmp/ny", "--preset", "ny"])
    )

    assert formal["local_couriers"] == 3000
    assert formal["couriers_per_platform"] == 500
    assert formal["deadline_seconds"] == 720
    assert ny["local_couriers"] == 300
    assert ny["couriers_per_platform"] == 50
    assert ny["deadline_seconds"] == 720
    assert PAPER_SUITE_PRESETS["chengdu-paper"]["ny"]["num_parcels"] == [500, 2000, 5000, 10000, 20000]


def test_explicit_flags_override_preset_background_defaults() -> None:
    """Caller-provided Exp-1 background options should win over preset values."""

    args = build_script_parser("test").parse_args(
        [
            "--output-dir",
            "/tmp/ny",
            "--preset",
            "ny",
            "--local-couriers",
            "321",
            "--couriers-per-platform",
            "75",
            "--deadline-seconds",
            "900",
        ]
    )
    fixed = build_fixed_config_from_args(args)

    assert fixed["local_couriers"] == 321
    assert fixed["couriers_per_platform"] == 75
    assert fixed["deadline_seconds"] == 900


def test_default_paper_algorithms_include_rl_capa_inference() -> None:
    """Paper experiments should expose checkpoint-based RL-CAPA inference by default."""

    assert "rl-capa-infer" in DEFAULT_CHENGDU_PAPER_ALGORITHMS
