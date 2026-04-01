"""Data models for the paper-faithful CAPA implementation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Hashable, List, Literal, Optional, Sequence


Location = Hashable


@dataclass(frozen=True)
class CAPAConfig:
    """Store paper-facing CAPA parameters used by CAMA, DAPA, and metrics."""

    batch_size: int = 1
    utility_balance_gamma: float = 0.5
    threshold_omega: float = 1.0
    local_payment_ratio_zeta: float = 0.2
    local_sharing_rate_mu1: float = 0.5
    cross_platform_sharing_rate_mu2: float = 0.4


@dataclass(frozen=True)
class Parcel:
    """Represent a pick-up parcel in the CAPA problem."""

    parcel_id: str
    location: Location
    arrival_time: int
    deadline: int
    weight: float
    fare: float


@dataclass
class Courier:
    """Represent a local or cross-platform courier and the pending route they carry."""

    courier_id: str
    current_location: Location
    depot_location: Location
    capacity: float
    current_load: float = 0.0
    route_locations: List[Location] = field(default_factory=list)
    available_from: int = 0
    alpha: float = 0.0
    beta: float = 0.0
    service_score: float = 0.0


@dataclass(frozen=True)
class CooperatingPlatform:
    """Represent a cooperating platform and its cross-platform couriers."""

    platform_id: str
    couriers: Sequence[Courier]
    base_price: float
    sharing_rate_gamma: float
    historical_quality: float


@dataclass(frozen=True)
class UtilityEvaluation:
    """Store the Eq.6 components for a courier-parcel pair."""

    value: float
    capacity_ratio: float
    detour_ratio: float
    insertion_index: int


@dataclass(frozen=True)
class CandidatePair:
    """Store a feasible local matching pair and its utility."""

    parcel: Parcel
    courier: Courier
    utility: UtilityEvaluation


@dataclass(frozen=True)
class PlatformBid:
    """Store the first-layer and second-layer bids for a candidate platform."""

    platform_id: str
    courier: Courier
    courier_bid: float
    platform_bid: float


@dataclass(frozen=True)
class Assignment:
    """Store the finalized parcel-courier assignment and realized revenues."""

    parcel: Parcel
    courier: Courier
    mode: Literal["local", "cross"]
    platform_id: Optional[str]
    courier_payment: float
    platform_payment: float
    local_platform_revenue: float
    cooperating_platform_revenue: float
    courier_revenue: float
    utility_value: Optional[float] = None


@dataclass(frozen=True)
class CAMAResult:
    """Collect the outputs of Algorithm 2."""

    local_assignments: Sequence[Assignment]
    auction_pool: Sequence[Parcel]
    all_feasible_pairs: Sequence[CandidatePair]
    candidate_best_pairs: Sequence[CandidatePair]
    threshold: float
    matching_pairs: Sequence[Assignment]


@dataclass(frozen=True)
class DAPAResult:
    """Collect the outputs of Algorithm 3."""

    cross_assignments: Sequence[Assignment]
    unassigned_parcels: Sequence[Parcel]
    platform_bids: Sequence[PlatformBid]


@dataclass(frozen=True)
class BatchReport:
    """Store per-batch CAPA outputs and timing information."""

    batch_index: int
    batch_time: int
    input_parcels: Sequence[Parcel]
    local_assignments: Sequence[Assignment]
    cross_assignments: Sequence[Assignment]
    unresolved_parcels: Sequence[Parcel]
    processing_time_seconds: float
    delivered_parcel_count: int = 0


@dataclass(frozen=True)
class RunMetrics:
    """Store the aggregate Phase 4 metrics required by the paper."""

    total_revenue: float
    completion_rate: float
    batch_processing_time: float
    delivered_parcel_count: int = 0
    accepted_parcel_count: int = 0


@dataclass(frozen=True)
class CAPAResult:
    """Store the end-to-end Algorithm 1 outputs."""

    matching_plan: Sequence[Assignment]
    unassigned_parcels: Sequence[Parcel]
    batch_reports: Sequence[BatchReport]
    metrics: RunMetrics
    delivered_parcels: Sequence[Parcel] = field(default_factory=list)
