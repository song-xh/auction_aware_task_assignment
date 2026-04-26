"""Actor-critic RL-CAPA environment aligned with the shared Chengdu batch flow.

This environment does not reimplement the Chengdu simulator. It wraps the
shared batch runtime from ``env.chengdu`` and only replaces the two paper
decision points:

1. Batch-size selection ``a_t^(1)``
2. Per-parcel cross-or-not decisions ``a_{t,i}``
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Dict, List, Mapping, Sequence, Tuple

import numpy as np

from capa.metrics import compute_total_revenue
from capa.models import Assignment, CAPAConfig, Courier, Parcel
from env.chengdu import (
    ChengduBatchRuntime,
    ChengduEnvironment,
    PreparedChengduBatch,
    finalize_chengdu_batch,
    finalize_chengdu_runtime,
    initialize_chengdu_batch_runtime,
    legacy_task_to_parcel,
    prepare_chengdu_batch,
    run_chengdu_cross_matching,
    run_chengdu_direct_local_matching,
)
from experiments.seeding import ChengduEnvironmentSeed, clone_environment_from_seed
from rl_capa.config import RLCAPAConfig
from rl_capa.state_builder import build_stage1_state, build_stage2_states


@dataclass(frozen=True)
class MatchingResult:
    """Store one local-matching round and the auction-pool parcel view."""

    local_assignments: Sequence[Assignment]
    auction_pool: Sequence[Parcel]


class RLCAPAEnv:
    """Wrap the shared Chengdu CAPA flow with RL-controlled decision points."""

    def __init__(
        self,
        environment_seed: ChengduEnvironmentSeed,
        capa_config: CAPAConfig,
        rl_config: RLCAPAConfig,
        cross_bid_window: int = 20,
    ) -> None:
        """Initialize the RL-CAPA environment wrapper.

        Args:
            environment_seed: Immutable seed used to reset each episode.
            capa_config: CAPA configuration reused by CAMA and DAPA.
            rl_config: RL-specific configuration such as batch action values.
            cross_bid_window: Window size for recent winning cross bids.
        """

        self._seed = environment_seed
        self._capa_config = capa_config
        self._rl_config = rl_config
        self._cross_bid_window = cross_bid_window

        self._environment: ChengduEnvironment | None = None
        self._runtime: ChengduBatchRuntime | None = None
        self._current_batch: PreparedChengduBatch | None = None
        self._current_remaining_tasks: list[Any] = []
        self._current_local_assignments: list[Assignment] = []
        self._current_batch_local_revenue: float = 0.0
        self._current_processing_started_at: float | None = None
        self._current_batch_duration: int = 0
        self._cross_bid_history: deque[float] = deque(maxlen=cross_bid_window)
        self._delivered_parcels: list[Parcel] = []
        self._episode_finalized: bool = False

    def reset(self) -> dict[str, Any]:
        """Reset the episode to the immutable seed state.

        Returns:
            Episode metadata including parcel count and start time.
        """

        self._environment = clone_environment_from_seed(self._seed)
        self._runtime = initialize_chengdu_batch_runtime(
            tasks=self._environment.tasks,
            local_couriers=self._environment.local_couriers,
            partner_couriers_by_platform=self._environment.partner_couriers_by_platform,
            station_set=self._environment.station_set,
            travel_model=self._environment.travel_model,
            config=self._capa_config,
            step_seconds=self._rl_config.step_seconds,
            platform_base_prices=self._environment.platform_base_prices,
            platform_sharing_rates=self._environment.platform_sharing_rates,
            platform_qualities=self._environment.platform_qualities,
            movement_callback=self._environment.movement_callback,
            service_radius_km=self._environment.service_radius_km,
            geo_index=self._environment.geo_index,
            speed_m_per_s=self._environment.travel_speed_m_per_s,
        )
        self._current_batch = None
        self._current_remaining_tasks = []
        self._current_local_assignments = []
        self._current_batch_local_revenue = 0.0
        self._current_processing_started_at = None
        self._current_batch_duration = 0
        self._cross_bid_history.clear()
        self._delivered_parcels = []
        self._episode_finalized = False
        return {
            "total_parcels": len(self._runtime.sorted_tasks),
            "start_time": self._runtime.current_time,
        }

    def get_stage1_state(self) -> np.ndarray:
        """Construct the 4-dimensional first-stage state ``s_t^(1)``."""

        runtime = self._require_runtime()
        pending_parcels = [legacy_task_to_parcel(task) for task in self._pending_tasks_before_next_batch()]
        local_couriers = self._snapshot_local_couriers()
        return build_stage1_state(
            pending_parcels=pending_parcels,
            local_couriers=local_couriers,
            travel_model=runtime.persistent_travel_model,
            now=runtime.current_time,
            service_radius_meters=runtime.service_radius_meters,
        )

    def apply_batch_size(self, batch_size: int) -> None:
        """Advance the shared Chengdu runtime by the chosen batch duration.

        Args:
            batch_size: Selected batch-size action value in seconds.
        """

        runtime = self._require_runtime()
        if batch_size not in self._rl_config.batch_action_values():
            raise ValueError(
                f"batch_size {batch_size} not in action space {self._rl_config.batch_action_values()}"
            )
        if self._current_batch is not None:
            raise RuntimeError("Previous batch has not been finalized yet.")
        self._current_batch = prepare_chengdu_batch(runtime, batch_size)
        self._current_remaining_tasks = []
        self._current_local_assignments = []
        self._current_batch_local_revenue = 0.0
        self._current_batch_duration = batch_size
        self._current_processing_started_at = (
            perf_counter() if self._current_batch.input_tasks else None
        )

    def current_eligible_parcels(self) -> List[Parcel]:
        """Return every parcel eligible for the active second-stage decision."""

        prepared_batch = self._require_current_batch()
        return [legacy_task_to_parcel(task) for task in prepared_batch.eligible_tasks]

    def get_stage2_states(self, parcels: Sequence[Parcel] | None = None) -> List[np.ndarray]:
        """Construct per-parcel second-stage states for the current full batch.

        Args:
            parcels: Optional parcel view. When omitted, states are built for
                all currently eligible batch parcels.

        Returns:
            One normalized raw feature vector per parcel.
        """

        runtime = self._require_runtime()
        target_parcels = list(self.current_eligible_parcels() if parcels is None else parcels)
        local_couriers = self._snapshot_local_couriers()
        cross_couriers = self._snapshot_partner_couriers()
        avg_cross_bid = (
            sum(self._cross_bid_history) / len(self._cross_bid_history)
            if self._cross_bid_history
            else 0.0
        )
        return build_stage2_states(
            unassigned_parcels=target_parcels,
            local_couriers=local_couriers,
            cross_courier_count=sum(1 for courier in cross_couriers if courier.available_from <= runtime.current_time),
            current_time=runtime.current_time,
            batch_size=self._current_batch_duration,
            local_payment_ratio=self._capa_config.local_payment_ratio_zeta,
            avg_cross_bid=avg_cross_bid,
        )

    def apply_stage2_decisions(self, decisions: Dict[str, int]) -> float:
        """Apply full-batch local-vs-cross decisions and finalize the batch.

        Args:
            decisions: Parcel decision mapping `{parcel_id: 0|1}` for every
                currently eligible parcel. `0` means direct local matching and
                `1` means cross-platform DAPA.

        Returns:
            Step revenue ``R_t`` for the current batch.
        """

        runtime = self._require_runtime()
        prepared_batch = self._require_current_batch()
        if not prepared_batch.input_tasks:
            self._clear_current_batch_state()
            return 0.0

        eligible_tasks = list(prepared_batch.eligible_tasks)
        task_lookup = {str(getattr(task, "num")): task for task in eligible_tasks}
        if eligible_tasks:
            missing = sorted(set(task_lookup) - set(decisions))
            extra = sorted(set(decisions) - set(task_lookup))
            if missing or extra:
                raise ValueError(
                    f"Decisions do not match eligible batch. Missing={missing} extra={extra}"
                )

        local_tasks: list[Any] = []
        auction_tasks: list[Any] = []
        for task in eligible_tasks:
            action = decisions[str(getattr(task, "num"))]
            if action == 1:
                auction_tasks.append(task)
            elif action == 0:
                local_tasks.append(task)
            else:
                raise ValueError(f"Invalid action {action} for parcel {getattr(task, 'num')}.")

        local_assignments, unresolved_local_tasks = run_chengdu_direct_local_matching(
            runtime=runtime,
            local_tasks=local_tasks,
            timing=prepared_batch.timing,
        )
        cross_assignments = run_chengdu_cross_matching(
            runtime=runtime,
            auction_tasks=auction_tasks,
            timing=prepared_batch.timing,
        )
        for assignment in cross_assignments:
            if assignment.platform_payment > 0:
                self._cross_bid_history.append(assignment.platform_payment)

        cross_assigned_ids = {assignment.parcel.parcel_id for assignment in cross_assignments}
        unresolved_tasks = [
            *unresolved_local_tasks,
            *(task for task in auction_tasks if str(getattr(task, "num")) not in cross_assigned_ids),
        ]
        processing_time_seconds = (
            0.0
            if self._current_processing_started_at is None
            else perf_counter() - self._current_processing_started_at
        )
        finalize_chengdu_batch(
            runtime=runtime,
            prepared_batch=prepared_batch,
            local_assignments=local_assignments,
            cross_assignments=cross_assignments,
            unresolved_tasks=unresolved_tasks,
            processing_time_seconds=processing_time_seconds,
        )
        step_revenue = compute_total_revenue([*local_assignments, *cross_assignments])
        self._clear_current_batch_state()
        return step_revenue

    def apply_cross_decisions(self, decisions: Dict[str, int]) -> float:
        """Backward-compatible alias for `apply_stage2_decisions`."""

        return self.apply_stage2_decisions(decisions)

    def finalize_episode(self) -> None:
        """Drain accepted legacy routes so evaluation uses delivered semantics."""

        runtime = self._require_runtime()
        if self._episode_finalized:
            return
        self._delivered_parcels = finalize_chengdu_runtime(runtime)
        self._episode_finalized = True

    def is_done(self) -> bool:
        """Return whether no future arrivals or unresolved backlog remain."""

        runtime = self._require_runtime()
        return runtime.next_task_index >= len(runtime.sorted_tasks) and not runtime.backlog and self._current_batch is None

    def accepted_assignments(self) -> Tuple[Assignment, ...]:
        """Return all accepted assignments committed during this episode."""

        runtime = self._require_runtime()
        return tuple(runtime.matching_plan)

    def batch_reports(self) -> Tuple[Any, ...]:
        """Return per-batch reports accumulated so far."""

        runtime = self._require_runtime()
        return tuple(runtime.batch_reports)

    def terminal_unassigned_tasks(self) -> Tuple[Any, ...]:
        """Return terminally unassigned legacy tasks."""

        runtime = self._require_runtime()
        return tuple(runtime.terminal_unassigned)

    def delivered_parcels(self) -> Tuple[Parcel, ...]:
        """Return physically delivered parcels after episode finalization."""

        return tuple(self._delivered_parcels)

    def total_parcel_count(self) -> int:
        """Return total parcel count for the active episode."""

        runtime = self._require_runtime()
        return len(runtime.sorted_tasks)

    @property
    def current_time(self) -> int:
        """Return the current Chengdu runtime time."""

        return self._require_runtime().current_time

    @property
    def current_batch_size(self) -> int:
        """Return the active first-stage action value for the in-flight batch."""

        if self._current_batch is None:
            return 0
        return self._current_batch_duration

    def _pending_tasks_before_next_batch(self) -> list[Any]:
        """Collect backlog plus tasks already arrived at the current batch boundary."""

        runtime = self._require_runtime()
        pending_tasks = list(runtime.backlog)
        pointer = runtime.next_task_index
        while pointer < len(runtime.sorted_tasks):
            task = runtime.sorted_tasks[pointer]
            if int(float(getattr(task, "s_time"))) <= runtime.current_time:
                pending_tasks.append(task)
                pointer += 1
                continue
            break
        return pending_tasks

    def _snapshot_local_couriers(self) -> list[Courier]:
        """Return current CAPA courier projections for the local platform."""

        runtime = self._require_runtime()
        return [
            runtime.snapshot_cache.get(courier, courier_id=f"local-{getattr(courier, 'num')}")
            for courier in runtime.active_local_couriers
        ]

    def _snapshot_partner_couriers(self) -> list[Courier]:
        """Return current CAPA courier projections for all partner platforms."""

        runtime = self._require_runtime()
        snapshots: list[Courier] = []
        for platform_id, couriers in runtime.active_partner_by_platform.items():
            for courier in couriers:
                snapshots.append(
                    runtime.snapshot_cache.get(
                        courier,
                        courier_id=f"{platform_id}-{getattr(courier, 'num')}",
                    )
                )
        return snapshots

    def _clear_current_batch_state(self) -> None:
        """Drop per-batch temporary state after finalization."""

        self._current_batch = None
        self._current_remaining_tasks = []
        self._current_local_assignments = []
        self._current_batch_local_revenue = 0.0
        self._current_processing_started_at = None
        self._current_batch_duration = 0

    def _require_runtime(self) -> ChengduBatchRuntime:
        """Return the initialized Chengdu runtime or raise."""

        if self._runtime is None:
            raise RuntimeError("Call reset() before interacting with the environment.")
        return self._runtime

    def _require_current_batch(self) -> PreparedChengduBatch:
        """Return the active prepared batch or raise."""

        if self._current_batch is None:
            raise RuntimeError("Call apply_batch_size() before using batch-level methods.")
        return self._current_batch


RLCAPAEnvironment = RLCAPAEnv
