"""Centralized CAPA, Chengdu adapter, and baseline default parameters."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import CAPAConfig


# Paper CAPA defaults
DEFAULT_CAPA_BATCH_SIZE = 300
DEFAULT_UTILITY_BALANCE_GAMMA = 0.5
DEFAULT_THRESHOLD_OMEGA = 1.0
DEFAULT_LOCAL_PAYMENT_RATIO_ZETA = 0.2
DEFAULT_LOCAL_SHARING_RATE_MU1 = 0.5
DEFAULT_CROSS_PLATFORM_SHARING_RATE_MU2 = 0.4

DEFAULT_PAPER_CAPA_RUNNER_KWARGS: dict[str, float] = {
    "utility_balance_gamma": DEFAULT_UTILITY_BALANCE_GAMMA,
    "threshold_omega": DEFAULT_THRESHOLD_OMEGA,
    "local_payment_ratio_zeta": DEFAULT_LOCAL_PAYMENT_RATIO_ZETA,
    "local_sharing_rate_mu1": DEFAULT_LOCAL_SHARING_RATE_MU1,
    "cross_platform_sharing_rate_mu2": DEFAULT_CROSS_PLATFORM_SHARING_RATE_MU2,
}

DEFAULT_LOWER_THRESHOLD_CAPA_RUNNER_KWARGS: dict[str, float] = {
    **DEFAULT_PAPER_CAPA_RUNNER_KWARGS,
    "threshold_omega": 0.8,
}

DEFAULT_DETOUR_FAVORING_CAPA_RUNNER_KWARGS: dict[str, float] = {
    **DEFAULT_LOWER_THRESHOLD_CAPA_RUNNER_KWARGS,
    "utility_balance_gamma": 0.3,
}


# Chengdu adapter defaults
DEFAULT_COURIER_PREFERENCE = 0.5
DEFAULT_COURIER_ALPHA = DEFAULT_COURIER_PREFERENCE
DEFAULT_COURIER_BETA = 1.0 - DEFAULT_COURIER_PREFERENCE
DEFAULT_COURIER_SERVICE_SCORE = 0.8

DEFAULT_PLATFORM_BASE_PRICE = 1.0
DEFAULT_PLATFORM_SHARING_RATE = DEFAULT_CROSS_PLATFORM_SHARING_RATE_MU2
DEFAULT_PLATFORM_QUALITY_START = 1.0
DEFAULT_PLATFORM_QUALITY_STEP = 0.1
MIN_PLATFORM_QUALITY = 0.5


# Baseline-specific defaults
DEFAULT_GREEDY_UTILITY = 0.5
DEFAULT_GREEDY_REALTIME = 1
DEFAULT_GREEDY_BASE_BID = 2.0

DEFAULT_GTA_UNIT_PRICE_PER_KM = 3.0
DEFAULT_IMPGTA_WINDOW_SECONDS = 180

DEFAULT_MRA_BASE_PRICE = 2.0
DEFAULT_MRA_SHARING_RATE = 0.5

DEFAULT_RAMCOM_RANDOM_SEED = 1


def build_default_capa_config(batch_size: int = DEFAULT_CAPA_BATCH_SIZE) -> "CAPAConfig":
    """Build a `CAPAConfig` instance from the centralized CAPA defaults.

    Args:
        batch_size: Batch window in seconds.

    Returns:
        One `CAPAConfig` populated with the standard paper defaults.
    """

    from .models import CAPAConfig

    return CAPAConfig(
        batch_size=batch_size,
        utility_balance_gamma=DEFAULT_UTILITY_BALANCE_GAMMA,
        threshold_omega=DEFAULT_THRESHOLD_OMEGA,
        local_payment_ratio_zeta=DEFAULT_LOCAL_PAYMENT_RATIO_ZETA,
        local_sharing_rate_mu1=DEFAULT_LOCAL_SHARING_RATE_MU1,
        cross_platform_sharing_rate_mu2=DEFAULT_CROSS_PLATFORM_SHARING_RATE_MU2,
    )


def build_default_platform_base_prices(platform_count: int) -> dict[str, float]:
    """Build the default cooperating-platform base-price mapping.

    Args:
        platform_count: Number of cooperating platforms.

    Returns:
        Mapping from platform identifier to the default base price.
    """

    return {
        f"P{index + 1}": DEFAULT_PLATFORM_BASE_PRICE
        for index in range(platform_count)
    }


def build_default_platform_sharing_rates(platform_count: int) -> dict[str, float]:
    """Build the default cooperating-platform sharing-rate mapping.

    Args:
        platform_count: Number of cooperating platforms.

    Returns:
        Mapping from platform identifier to the default sharing rate.
    """

    return {
        f"P{index + 1}": DEFAULT_PLATFORM_SHARING_RATE
        for index in range(platform_count)
    }


def build_default_platform_qualities(platform_count: int) -> dict[str, float]:
    """Build the default cooperating-platform quality mapping.

    Args:
        platform_count: Number of cooperating platforms.

    Returns:
        Mapping from platform identifier to the default descending quality series.
    """

    return {
        f"P{index + 1}": max(
            MIN_PLATFORM_QUALITY,
            DEFAULT_PLATFORM_QUALITY_START - (DEFAULT_PLATFORM_QUALITY_STEP * index),
        )
        for index in range(platform_count)
    }
