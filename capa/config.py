"""Centralized CAPA, Chengdu adapter, and baseline default parameters."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import CAPAConfig


# 论文 CAPA 默认参数
DEFAULT_CAPA_BATCH_SIZE = 300
# 算法 1 中的批大小阈值 Δb，表示将到达包裹流累积成一个 batch 的时间窗口。

DEFAULT_UTILITY_BALANCE_GAMMA = 0.5
# Eq.(6) 中的平衡系数 γ，用于权衡容量比 Δwτ 与绕路比 Δdτ 对局部匹配效用 u(τ,c) 的影响。

DEFAULT_THRESHOLD_OMEGA = 1.0
# Eq.(7) 中的敏感性调节因子 ω，用于把候选匹配对平均效用缩放成动态阈值 Th。

DEFAULT_LOCAL_PAYMENT_RATIO_ZETA = 0.2
# 本地骑手固定报酬比例 ζ，对应论文中的 Rc(τ,c)=ζ·pτ。

DEFAULT_LOCAL_SHARING_RATE_MU1 = 0.5
# Loc 的第一层共享比例 μ1，用于定义 p'τ = μ1·pτ，即本地平台愿意给跨平台骑手的最高起始支付上界。

DEFAULT_CROSS_PLATFORM_SHARING_RATE_MU2 = 0.4
# Loc 的第二层共享比例 μ2，用于平台层拍卖奖励与支付上界；论文要求 μ1 + μ2 ≤ 1。

DEFAULT_PAPER_CAPA_RUNNER_KWARGS: dict[str, float] = {
    "utility_balance_gamma": DEFAULT_UTILITY_BALANCE_GAMMA,
    "threshold_omega": DEFAULT_THRESHOLD_OMEGA,
    "local_payment_ratio_zeta": DEFAULT_LOCAL_PAYMENT_RATIO_ZETA,
    "local_sharing_rate_mu1": DEFAULT_LOCAL_SHARING_RATE_MU1,
    "cross_platform_sharing_rate_mu2": DEFAULT_CROSS_PLATFORM_SHARING_RATE_MU2,
}
# 论文主实验的 CAPA 默认敏感性参数组合。

DEFAULT_LOWER_THRESHOLD_CAPA_RUNNER_KWARGS: dict[str, float] = {
    **DEFAULT_PAPER_CAPA_RUNNER_KWARGS,
    "threshold_omega": 0.8,
}
# 仅降低 Eq.(7) 动态阈值敏感因子 ω 的实验配置，用于让更多包裹留在本地匹配阶段。

DEFAULT_DETOUR_FAVORING_CAPA_RUNNER_KWARGS: dict[str, float] = {
    **DEFAULT_LOWER_THRESHOLD_CAPA_RUNNER_KWARGS,
    "utility_balance_gamma": 0.3,
}
# 在较低阈值基础上进一步降低 γ，使效用更偏向绕路因素而非容量因素。


# 成都适配层默认参数
DEFAULT_COURIER_PREFERENCE = 0.5
# 成都环境里把骑手偏好压缩成一个对称默认值；论文中 α 与 β 为骑手对绕路/服务质量的偏好系数，实验通常均匀生成。

DEFAULT_COURIER_ALPHA = DEFAULT_COURIER_PREFERENCE
# 成都适配层默认 α，表示跨平台骑手对绕路比 Δdτ 的偏好权重。

DEFAULT_COURIER_BETA = 1.0 - DEFAULT_COURIER_PREFERENCE
# 成都适配层默认 β，表示跨平台骑手对历史服务表现 g(c) 的偏好权重；这里保持 α+β=1。

DEFAULT_COURIER_SERVICE_SCORE = 0.8
# 成都适配层默认的历史服务表现 g(c) 代理值；论文中 g(c) 由质量、效率、顾客满意度三项历史得分平均得到。

DEFAULT_PLATFORM_BASE_PRICE = 1.0
# 成都适配层默认的 p_min / base price，对应 Eq.(1) 中合作平台控制跨平台骑手报价下界的基础价格。

DEFAULT_PLATFORM_SHARING_RATE = DEFAULT_CROSS_PLATFORM_SHARING_RATE_MU2
# 成都适配层默认的合作平台共享率 γ，对应 Eq.(1) 中平台 P 对一层骑手报价的缩放系数。

DEFAULT_PLATFORM_QUALITY_START = 1.0
# 成都适配层生成 f(P) 历史合作质量代理值时的起始值；论文中的 f(P) 来源于平台与 Loc 的历史合作质量。

DEFAULT_PLATFORM_QUALITY_STEP = 0.1
# 成都适配层生成不同平台质量差异时的递减步长，用于构造一组单调下降的历史合作质量代理值。

MIN_PLATFORM_QUALITY = 0.5
# 成都适配层历史合作质量代理值的下界，避免生成非正或过小的 f(P)。


# Baseline 私有参数
DEFAULT_GREEDY_UTILITY = 0.5
# Greedy 基线的局部报价缩放系数 u；非 CAPA 论文主参数，只用于 legacy Greedy 规则。

DEFAULT_GREEDY_REALTIME = 1
# Greedy 基线的仿真推进步长（秒）；非 CAPA 论文主参数。

DEFAULT_GREEDY_BASE_BID = 2.0
# Greedy 基线的基础报价偏移项；非 CAPA 论文主参数。

DEFAULT_GTA_UNIT_PRICE_PER_KM = 3.0
# GTA / BaseGTA / ImpGTA 中单位公里派单成本；对应参考文献 [17] 的 dispatch cost 设定，不属于 CAPA 主参数。

DEFAULT_IMPGTA_WINDOW_SECONDS = 180
# ImpGTA 的预测窗口大小（秒）；属于 baseline 私有配置，不属于 CAPA 主参数。

DEFAULT_IMPGTA_PREDICTION_SUCCESS_RATE = 0.8
# ImpGTA 简化预测逻辑中的预测成功率；1.0 表示完全看到未来窗口，0.0 表示完全看不到。

DEFAULT_IMPGTA_PREDICTION_SAMPLING_SEED = 1
# ImpGTA 简化预测逻辑里对未来窗口做成功率抽样时使用的确定性随机种子。

DEFAULT_MRA_BASE_PRICE = 2.0
# MRA 基线的基础报价偏移项；非 CAPA 论文主参数。

DEFAULT_MRA_SHARING_RATE = 0.5
# MRA 基线的票价缩放系数；非 CAPA 论文主参数。

DEFAULT_RAMCOM_RANDOM_SEED = 1
# RamCOM 基线的默认随机种子；非 CAPA 论文主参数。


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
