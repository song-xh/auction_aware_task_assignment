"""Regression tests for centralized CAPA and baseline configuration defaults."""

from __future__ import annotations

import inspect
import unittest
from types import SimpleNamespace

from algorithms.impgta_runner import build_impgta_runner
from algorithms.ramcom_runner import build_ramcom_runner
from baselines import gta, mra
from baselines.common import project_courier_to_capa
from baselines.greedy import run_greedy_baseline_environment, run_legacy_greedy_stdout
from capa.config import (
    DEFAULT_CAPA_BATCH_SIZE,
    DEFAULT_COURIER_ALPHA,
    DEFAULT_COURIER_BETA,
    DEFAULT_COURIER_PREFERENCE,
    DEFAULT_COURIER_SERVICE_SCORE,
    DEFAULT_CROSS_PLATFORM_SHARING_RATE_MU2,
    DEFAULT_DETOUR_FAVORING_CAPA_RUNNER_KWARGS,
    DEFAULT_GREEDY_REALTIME,
    DEFAULT_GREEDY_UTILITY,
    DEFAULT_IMPGTA_WINDOW_SECONDS,
    DEFAULT_LOWER_THRESHOLD_CAPA_RUNNER_KWARGS,
    DEFAULT_LOCAL_PAYMENT_RATIO_ZETA,
    DEFAULT_LOCAL_SHARING_RATE_MU1,
    DEFAULT_MRA_BASE_PRICE,
    DEFAULT_MRA_SHARING_RATE,
    DEFAULT_PAPER_CAPA_RUNNER_KWARGS,
    DEFAULT_PLATFORM_BASE_PRICE,
    DEFAULT_PLATFORM_SHARING_RATE,
    DEFAULT_RAMCOM_RANDOM_SEED,
    DEFAULT_THRESHOLD_OMEGA,
    DEFAULT_UTILITY_BALANCE_GAMMA,
    DEFAULT_GTA_UNIT_PRICE_PER_KM,
    MIN_PLATFORM_QUALITY,
    build_default_platform_base_prices,
    build_default_platform_qualities,
    build_default_platform_sharing_rates,
)
from capa.experiments import build_default_chengdu_config
from capa.models import CAPAConfig
from env.chengdu import legacy_courier_to_capa
from experiments.paper_chengdu import DEFAULT_EXP1_ROUNDS


class CAPAConfigCentralizationTests(unittest.TestCase):
    """Verify CAPA paper defaults and baseline defaults come from one config module."""

    def test_capa_config_defaults_match_centralized_constants(self) -> None:
        """`CAPAConfig()` should expose the centralized paper defaults."""

        self.assertEqual(
            CAPAConfig(),
            CAPAConfig(
                batch_size=DEFAULT_CAPA_BATCH_SIZE,
                utility_balance_gamma=DEFAULT_UTILITY_BALANCE_GAMMA,
                threshold_omega=DEFAULT_THRESHOLD_OMEGA,
                local_payment_ratio_zeta=DEFAULT_LOCAL_PAYMENT_RATIO_ZETA,
                local_sharing_rate_mu1=DEFAULT_LOCAL_SHARING_RATE_MU1,
                cross_platform_sharing_rate_mu2=DEFAULT_CROSS_PLATFORM_SHARING_RATE_MU2,
            ),
        )

    def test_default_chengdu_config_reuses_centralized_defaults(self) -> None:
        """The Chengdu experiment builder should only override batch size."""

        config = build_default_chengdu_config(batch_size=120)

        self.assertEqual(config.batch_size, 120)
        self.assertEqual(config.utility_balance_gamma, DEFAULT_UTILITY_BALANCE_GAMMA)
        self.assertEqual(config.threshold_omega, DEFAULT_THRESHOLD_OMEGA)
        self.assertEqual(config.local_payment_ratio_zeta, DEFAULT_LOCAL_PAYMENT_RATIO_ZETA)
        self.assertEqual(config.local_sharing_rate_mu1, DEFAULT_LOCAL_SHARING_RATE_MU1)
        self.assertEqual(config.cross_platform_sharing_rate_mu2, DEFAULT_CROSS_PLATFORM_SHARING_RATE_MU2)

    def test_exp1_rounds_reuse_centralized_presets(self) -> None:
        """Managed Exp-1 presets should match the centralized CAPA runner presets."""

        self.assertEqual(DEFAULT_EXP1_ROUNDS[0].capa_runner_kwargs, DEFAULT_PAPER_CAPA_RUNNER_KWARGS)
        self.assertEqual(DEFAULT_EXP1_ROUNDS[1].capa_runner_kwargs, DEFAULT_LOWER_THRESHOLD_CAPA_RUNNER_KWARGS)
        self.assertEqual(DEFAULT_EXP1_ROUNDS[2].capa_runner_kwargs, DEFAULT_DETOUR_FAVORING_CAPA_RUNNER_KWARGS)

    def test_courier_fallback_defaults_are_shared(self) -> None:
        """Legacy and baseline courier projections should use the same fallback defaults."""

        station = SimpleNamespace(l_node="depot")
        legacy = SimpleNamespace(
            station=station,
            location="loc",
            max_weight=20.0,
            re_weight=5.0,
            re_schedule=[],
        )
        projected_legacy = legacy_courier_to_capa(legacy, courier_id="legacy")
        self.assertEqual(projected_legacy.alpha, DEFAULT_COURIER_ALPHA)
        self.assertEqual(projected_legacy.beta, DEFAULT_COURIER_BETA)
        self.assertEqual(projected_legacy.service_score, DEFAULT_COURIER_SERVICE_SCORE)

        fallback = SimpleNamespace(location="loc", max_weight=20.0, re_weight=5.0, re_schedule=[])
        projected_fallback = project_courier_to_capa(fallback, courier_id="fallback")
        self.assertEqual(projected_fallback.alpha, DEFAULT_COURIER_ALPHA)
        self.assertEqual(projected_fallback.beta, DEFAULT_COURIER_BETA)
        self.assertEqual(projected_fallback.service_score, DEFAULT_COURIER_SERVICE_SCORE)

    def test_platform_default_builders_match_expected_values(self) -> None:
        """Default Chengdu platform dictionaries should come from shared builders."""

        self.assertEqual(
            build_default_platform_base_prices(3),
            {"P1": DEFAULT_PLATFORM_BASE_PRICE, "P2": DEFAULT_PLATFORM_BASE_PRICE, "P3": DEFAULT_PLATFORM_BASE_PRICE},
        )
        self.assertEqual(
            build_default_platform_sharing_rates(3),
            {"P1": DEFAULT_PLATFORM_SHARING_RATE, "P2": DEFAULT_PLATFORM_SHARING_RATE, "P3": DEFAULT_PLATFORM_SHARING_RATE},
        )
        self.assertEqual(
            build_default_platform_qualities(4),
            {"P1": 1.0, "P2": 0.9, "P3": 0.8, "P4": max(MIN_PLATFORM_QUALITY, 0.7)},
        )

    def test_baseline_default_sources_are_centralized(self) -> None:
        """Baseline defaults and unified runners should resolve to the centralized constants."""

        greedy_signature = inspect.signature(run_greedy_baseline_environment)
        self.assertEqual(greedy_signature.parameters["utility"].default, DEFAULT_GREEDY_UTILITY)
        self.assertEqual(greedy_signature.parameters["realtime"].default, DEFAULT_GREEDY_REALTIME)
        self.assertEqual(greedy_signature.parameters["local_payment_ratio"].default, DEFAULT_LOCAL_PAYMENT_RATIO_ZETA)

        legacy_greedy_signature = inspect.signature(run_legacy_greedy_stdout)
        self.assertEqual(legacy_greedy_signature.parameters["utility"].default, DEFAULT_GREEDY_UTILITY)
        self.assertEqual(legacy_greedy_signature.parameters["realtime"].default, DEFAULT_GREEDY_REALTIME)

        self.assertEqual(gta.DEFAULT_UNIT_PRICE_PER_KM, DEFAULT_GTA_UNIT_PRICE_PER_KM)
        self.assertEqual(gta.DEFAULT_IMPGTA_WINDOW_SECONDS, DEFAULT_IMPGTA_WINDOW_SECONDS)
        self.assertEqual(mra.DEFAULT_MRA_BASE_PRICE, DEFAULT_MRA_BASE_PRICE)
        self.assertEqual(mra.DEFAULT_MRA_SHARING_RATE, DEFAULT_MRA_SHARING_RATE)

        impgta_signature = inspect.signature(build_impgta_runner)
        self.assertEqual(impgta_signature.parameters["prediction_window_seconds"].default, DEFAULT_IMPGTA_WINDOW_SECONDS)

        ramcom_signature = inspect.signature(build_ramcom_runner)
        self.assertEqual(ramcom_signature.parameters["random_seed"].default, DEFAULT_RAMCOM_RANDOM_SEED)

    def test_courier_preference_constant_matches_current_adapter_split(self) -> None:
        """The centralized courier preference should still map to the current symmetric split."""

        self.assertEqual(DEFAULT_COURIER_PREFERENCE, DEFAULT_COURIER_ALPHA)
        self.assertEqual(DEFAULT_COURIER_BETA, 1.0 - DEFAULT_COURIER_PREFERENCE)


if __name__ == "__main__":
    unittest.main()
