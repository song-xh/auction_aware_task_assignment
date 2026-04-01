"""Paper-faithful revenue helpers shared by CAPA and baseline evaluations."""

from __future__ import annotations


DEFAULT_LOCAL_PAYMENT_RATIO = 0.2


def compute_local_courier_payment(parcel_fare: float, local_payment_ratio: float = DEFAULT_LOCAL_PAYMENT_RATIO) -> float:
    """Return the fixed local-courier payment `Rc(tau, c) = zeta * p_tau`.

    Args:
        parcel_fare: Fare of the completed pick-up parcel.
        local_payment_ratio: Fixed local payment ratio `zeta`.

    Returns:
        The payment from the local platform to the selected inner courier.
    """

    return float(local_payment_ratio) * float(parcel_fare)


def compute_local_platform_revenue_for_local_completion(
    parcel_fare: float,
    local_payment_ratio: float = DEFAULT_LOCAL_PAYMENT_RATIO,
) -> float:
    """Return the paper's local-platform revenue for an inner-courier completion.

    Args:
        parcel_fare: Fare of the completed pick-up parcel.
        local_payment_ratio: Fixed local payment ratio `zeta`.

    Returns:
        `p_tau - Rc(tau, c)` under Definition 4 and Eq. 5.
    """

    return float(parcel_fare) - compute_local_courier_payment(parcel_fare, local_payment_ratio)


def compute_local_platform_revenue_for_cross_completion(parcel_fare: float, platform_payment: float) -> float:
    """Return the paper's local-platform revenue for a cross-platform completion.

    Args:
        parcel_fare: Fare of the completed pick-up parcel.
        platform_payment: Final payment `p'(tau, c)` to the winning cooperating platform.

    Returns:
        `p_tau - p'(tau, c)` under Definition 4 and Eq. 5.
    """

    return float(parcel_fare) - float(platform_payment)


def compute_cooperating_platform_revenue(platform_payment: float, courier_payment: float) -> float:
    """Return the cooperating platform's profit under the paper's DLAM settlement.

    Args:
        platform_payment: Payment from the local platform to the winning cooperating platform.
        courier_payment: Payment from the cooperating platform to its winning courier.

    Returns:
        The cooperating platform's retained profit.
    """

    return float(platform_payment) - float(courier_payment)
