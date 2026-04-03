"""Shared RL-CAPA environment built on top of the Chengdu unified environment."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, MutableSequence, Sequence

import numpy as np

from capa.cama import run_cama
from capa.dapa import run_dapa
from capa.metrics import compute_total_revenue
from capa.models import Assignment, CAPAConfig, Parcel
from env.chengdu import (
    ChengduEnvironment,
    apply_assignment_to_legacy_courier,
    bind_assignment_to_legacy_objects,
    current_legacy_route_task_ids,
    flatten_partner_couriers,
    framework_movement_callback,
    legacy_courier_to_capa,
    legacy_platform_to_capa,
    legacy_task_to_parcel,
)
from experiments.seeding import ChengduEnvironmentSeed, clone_environment_from_seed

from .config import RLCAPAConfig
from .state import build_batch_state, build_parcel_state
from .transitions import BatchDecisionContext, RLCAPAStepResult, Transition
from capa.utility import find_best_local_insertion


@dataclass
class _PendingParcelDecision:
    """Store one unresolved `M_m` decision until the next batch state is known."""

    parcel_id: str
    parcel: Parcel
    state: np.ndarray
    action: int


class RLCAPAEnvironment:
    """Wrap the shared Chengdu environment to expose the two RL-CAPA decision layers."""

    def __init__(
        self,
        environment_seed: ChengduEnvironmentSeed,
        capa_config: CAPAConfig,
        rl_config: RLCAPAConfig,
    ) -> None:
        """Store the immutable episode seed and the CAPA / RL configuration."""
        self._seed = environment_seed
        self._capa_config = capa_config
        self._rl_config = rl_config
        self._environment: ChengduEnvironment | None = None
        self._tasks: list[Any] = []
        self._next_task_index = 0
        self._current_time = 0
        self._carry_tasks: list[Any] = []
        self._pending_parcel_decisions: dict[str, _PendingParcelDecision] = {}
        self._resolved_terminal_parcel_transitions: list[Transition] = []
        self._accepted_assignments: list[Assignment] = []

    def reset(self) -> np.ndarray:
        """Reset one RL episode from the immutable Chengdu seed and return the first `S_b`."""
        self._environment = clone_environment_from_seed(self._seed)
        self._tasks = sorted(
            list(self._environment.tasks),
            key=lambda item: (float(getattr(item, "s_time")), float(getattr(item, "d_time")), str(getattr(item, "num"))),
        )
        self._next_task_index = 0
        self._current_time = int(float(getattr(self._tasks[0], "s_time"))) if self._tasks else 0
        self._carry_tasks = []
        self._pending_parcel_decisions = {}
        self._resolved_terminal_parcel_transitions = []
        self._accepted_assignments = []
        return self._build_current_batch_state()

    def is_terminal(self) -> bool:
        """Return whether the episode has exhausted all tasks and carry-over parcels."""
        return self._next_task_index >= len(self._tasks) and not self._carry_tasks and not self._pending_parcel_decisions

    def start_batch(self, batch_duration: int) -> BatchDecisionContext:
        """Advance the base environment by one chosen batch duration and expose `L_cr` parcel states."""
        if self._environment is None:
            raise RuntimeError("RLCAPAEnvironment.reset() must be called before start_batch().")
        if batch_duration not in self._rl_config.batch_action_values():
            raise ValueError(f"Unsupported batch_duration {batch_duration}; must belong to A_b.")

        batch_state = self._build_current_batch_state()
        batch_start_time = self._current_time
        batch_end_time = batch_start_time + batch_duration
        movement = self._environment.movement_callback or framework_movement_callback
        movement(
            list(self._environment.local_couriers),
            flatten_partner_couriers(self._environment.partner_couriers_by_platform),
            batch_duration,
            self._environment.station_set,
        )

        batch_tasks = list(self._carry_tasks)
        while self._next_task_index < len(self._tasks):
            task = self._tasks[self._next_task_index]
            task_arrival = int(float(getattr(task, "s_time")))
            if task_arrival < batch_end_time:
                batch_tasks.append(task)
                self._next_task_index += 1
                continue
            break
        self._carry_tasks = []
        self._current_time = batch_end_time

        local_assignments: list[Assignment] = []
        auction_pool: list[Parcel] = []
        if batch_tasks:
            local_assignments, auction_pool = self._run_local_matching(batch_tasks=batch_tasks)
            self._accepted_assignments.extend(local_assignments)

        resolved_transitions = self._resolve_pending_parcel_transitions(
            auction_pool=auction_pool,
            local_assignments=local_assignments,
            batch_duration=batch_duration,
        )
        parcel_states = {
            parcel.parcel_id: build_parcel_state(
                parcel=parcel,
                unassigned_count=len(auction_pool),
                current_time=self._current_time,
                batch_size=batch_duration,
            )
            for parcel in auction_pool
        }
        return BatchDecisionContext(
            batch_state=batch_state,
            batch_duration=batch_duration,
            batch_time=self._current_time,
            batch_parcels=[legacy_task_to_parcel(task) for task in batch_tasks],
            local_assignments=local_assignments,
            auction_pool=auction_pool,
            parcel_states=parcel_states,
            resolved_parcel_transitions=tuple(resolved_transitions),
        )

    def apply_parcel_actions(
        self,
        context: BatchDecisionContext,
        parcel_actions: Mapping[str, int],
    ) -> RLCAPAStepResult:
        """Finalize one batch after the parcel-level `M_m` decisions have been chosen."""
        if self._environment is None:
            raise RuntimeError("RLCAPAEnvironment.reset() must be called before apply_parcel_actions().")
        auction_lookup = {parcel.parcel_id: parcel for parcel in context.auction_pool}
        cross_ids = set()
        parcel_transitions: list[Transition] = []
        for parcel_id, state in context.parcel_states.items():
            if parcel_id not in parcel_actions:
                raise ValueError(f"Missing action for parcel {parcel_id}.")
            action = int(parcel_actions[parcel_id])
            if action not in {0, 1}:
                raise ValueError(f"Invalid cross-or-not action {action} for parcel {parcel_id}.")
            if action == 1:
                cross_ids.add(parcel_id)
            else:
                self._pending_parcel_decisions[parcel_id] = _PendingParcelDecision(
                    parcel_id=parcel_id,
                    parcel=auction_lookup[parcel_id],
                    state=state,
                    action=action,
                )
                self._carry_tasks.append(self._task_from_parcel_id(parcel_id))

        cross_assignments = self._run_cross_matching(
            parcels=[auction_lookup[parcel_id] for parcel_id in cross_ids],
        )
        assigned_cross_ids = {assignment.parcel.parcel_id for assignment in cross_assignments}
        for parcel_id in cross_ids:
            state = context.parcel_states[parcel_id]
            if parcel_id in assigned_cross_ids:
                assignment = next(item for item in cross_assignments if item.parcel.parcel_id == parcel_id)
                parcel_transitions.append(
                    Transition(
                        state=state,
                        action=1,
                        reward=assignment.local_platform_revenue,
                        next_state=np.zeros_like(state),
                        done=True,
                    )
                )
                continue
            self._pending_parcel_decisions[parcel_id] = _PendingParcelDecision(
                parcel_id=parcel_id,
                parcel=auction_lookup[parcel_id],
                state=state,
                action=1,
            )
            self._carry_tasks.append(self._task_from_parcel_id(parcel_id))

        batch_reward = compute_total_revenue([*context.local_assignments, *cross_assignments])
        next_batch_state = self._build_current_batch_state()
        batch_transition = Transition(
            state=context.batch_state,
            action=self._rl_config.batch_duration_to_action_index(context.batch_duration),
            reward=batch_reward,
            next_state=next_batch_state,
            done=self.is_terminal(),
        )
        return RLCAPAStepResult(
            batch_transition=batch_transition,
            batch_reward=batch_reward,
            parcel_transitions=tuple(parcel_transitions),
            local_assignments=context.local_assignments,
            cross_assignments=tuple(cross_assignments),
            next_batch_state=next_batch_state,
            done=self.is_terminal(),
        )

    def finish_episode(self) -> list[Transition]:
        """Finalize any still-unresolved parcel decisions with terminal zero reward."""
        terminal_transitions: list[Transition] = []
        for pending in self._pending_parcel_decisions.values():
            terminal_transitions.append(
                Transition(
                    state=pending.state,
                    action=pending.action,
                    reward=0.0,
                    next_state=np.zeros_like(pending.state),
                    done=True,
                )
            )
        self._pending_parcel_decisions = {}
        return terminal_transitions

    def accepted_assignments(self) -> tuple[Assignment, ...]:
        """Return all accepted assignments committed during the current episode."""

        return tuple(self._accepted_assignments)

    def total_parcel_count(self) -> int:
        """Return the total number of parcels represented by the immutable episode seed."""

        return len(self._seed.tasks)

    def drain_routes(self) -> int:
        """Advance the shared Chengdu environment until all accepted routes are empty."""

        if self._environment is None:
            raise RuntimeError("RLCAPAEnvironment.reset() must be called before drain_routes().")
        return self._environment.drain(step_seconds=self._rl_config.step_seconds)

    def _build_current_batch_state(self) -> np.ndarray:
        """Build the current `S_b` feature vector from carry-over and arrived tasks."""
        pending_tasks = list(self._carry_tasks)
        pointer = self._next_task_index
        while pointer < len(self._tasks):
            task = self._tasks[pointer]
            if int(float(getattr(task, "s_time"))) <= self._current_time:
                pending_tasks.append(task)
                pointer += 1
                continue
            break
        pending_parcels = [legacy_task_to_parcel(task) for task in pending_tasks]
        local_snapshots = [
            legacy_courier_to_capa(courier, courier_id=f"local-{getattr(courier, 'num')}")
            for courier in self._environment.local_couriers
        ] if self._environment is not None else []
        service_radius_meters = None
        if self._environment is not None and self._environment.service_radius_km is not None:
            service_radius_meters = float(self._environment.service_radius_km) * 1000.0
        return build_batch_state(
            pending_parcels=pending_parcels,
            local_couriers=local_snapshots,
            travel_model=self._environment.travel_model if self._environment is not None else None,
            now=self._current_time,
            service_radius_meters=service_radius_meters,
        )

    def _run_local_matching(self, batch_tasks: Sequence[Any]) -> tuple[list[Assignment], list[Parcel]]:
        """Execute CAMA over the current batch and commit local assignments to the legacy environment."""
        local_snapshots = [
            legacy_courier_to_capa(courier, courier_id=f"local-{getattr(courier, 'num')}")
            for courier in self._environment.local_couriers
        ]
        arrived_parcels = [legacy_task_to_parcel(task) for task in batch_tasks]
        service_radius_meters = None if self._environment.service_radius_km is None else float(self._environment.service_radius_km) * 1000.0
        cama_result = run_cama(
            parcels=arrived_parcels,
            couriers=local_snapshots,
            travel_model=self._environment.travel_model,
            config=self._capa_config,
            now=self._current_time,
            service_radius_meters=service_radius_meters,
        )
        best_local_pairs = {
            (pair.parcel.parcel_id, pair.courier.courier_id): pair.utility.insertion_index
            for pair in cama_result.candidate_best_pairs
        }
        task_lookup = {parcel.parcel_id: task for parcel, task in zip(arrived_parcels, batch_tasks)}
        local_lookup = {f"local-{getattr(courier, 'num')}": courier for courier in self._environment.local_couriers}
        local_assignments: list[Assignment] = []
        for assignment in cama_result.local_assignments:
            task = task_lookup[assignment.parcel.parcel_id]
            legacy_courier = local_lookup[assignment.courier.courier_id]
            insertion_index = best_local_pairs[(assignment.parcel.parcel_id, assignment.courier.courier_id)]
            apply_assignment_to_legacy_courier(task, legacy_courier, insertion_index)
            local_assignments.append(bind_assignment_to_legacy_objects(assignment, task, legacy_courier))
        return local_assignments, list(cama_result.auction_pool)

    def _run_cross_matching(self, parcels: Sequence[Parcel]) -> list[Assignment]:
        """Execute DAPA for the selected cross-platform parcels and commit successful assignments."""
        if not parcels:
            return []
        partner_lookup = {
            platform_id: {f"{platform_id}-{getattr(courier, 'num')}": courier for courier in couriers}
            for platform_id, couriers in self._environment.partner_couriers_by_platform.items()
        }
        partner_platforms = [
            legacy_platform_to_capa(
                platform_id=platform_id,
                couriers=couriers,
                base_price=self._environment.platform_base_prices[platform_id],
                sharing_rate_gamma=self._environment.platform_sharing_rates[platform_id],
                historical_quality=self._environment.platform_qualities[platform_id],
            )
            for platform_id, couriers in self._environment.partner_couriers_by_platform.items()
        ]
        snapshot_lookup = {
            platform.platform_id: {courier.courier_id: courier for courier in platform.couriers}
            for platform in partner_platforms
        }
        service_radius_meters = None if self._environment.service_radius_km is None else float(self._environment.service_radius_km) * 1000.0
        dapa_result = run_dapa(
            parcels=parcels,
            platforms=partner_platforms,
            travel_model=self._environment.travel_model,
            config=self._capa_config,
            now=self._current_time,
            service_radius_meters=service_radius_meters,
        )
        task_lookup = {parcel.parcel_id: self._task_from_parcel_id(parcel.parcel_id) for parcel in parcels}
        realized_assignments: list[Assignment] = []
        for assignment in dapa_result.cross_assignments:
            task = task_lookup[assignment.parcel.parcel_id]
            legacy_courier = partner_lookup[assignment.platform_id][assignment.courier.courier_id]
            snapshot_courier = snapshot_lookup[assignment.platform_id][assignment.courier.courier_id]
            _, insertion_index = find_best_local_insertion(
                legacy_task_to_parcel(task),
                snapshot_courier,
                self._environment.travel_model,
            )
            apply_assignment_to_legacy_courier(task, legacy_courier, insertion_index)
            realized_assignments.append(bind_assignment_to_legacy_objects(assignment, task, legacy_courier))
        self._accepted_assignments.extend(realized_assignments)
        return realized_assignments

    def _resolve_pending_parcel_transitions(
        self,
        auction_pool: Sequence[Parcel],
        local_assignments: Sequence[Assignment],
        batch_duration: int,
    ) -> list[Transition]:
        """Resolve deferred or failed cross transitions once the next parcel state becomes observable."""
        resolved: list[Transition] = []
        local_lookup = {assignment.parcel.parcel_id: assignment for assignment in local_assignments}
        auction_lookup = {parcel.parcel_id: parcel for parcel in auction_pool}
        for parcel_id, pending in list(self._pending_parcel_decisions.items()):
            if parcel_id in local_lookup:
                assignment = local_lookup[parcel_id]
                resolved.append(
                    Transition(
                        state=pending.state,
                        action=pending.action,
                        reward=assignment.local_platform_revenue,
                        next_state=np.zeros_like(pending.state),
                        done=True,
                    )
                )
                del self._pending_parcel_decisions[parcel_id]
                continue
            if parcel_id in auction_lookup:
                resolved.append(
                    Transition(
                        state=pending.state,
                        action=pending.action,
                        reward=0.0,
                        next_state=build_parcel_state(
                            parcel=auction_lookup[parcel_id],
                            unassigned_count=len(auction_pool),
                            current_time=self._current_time,
                            batch_size=batch_duration,
                        ),
                        done=False,
                    )
                )
                del self._pending_parcel_decisions[parcel_id]
                continue
            resolved.append(
                Transition(
                    state=pending.state,
                    action=pending.action,
                    reward=0.0,
                    next_state=np.zeros_like(pending.state),
                    done=True,
                )
            )
            del self._pending_parcel_decisions[parcel_id]
        return resolved

    def _task_from_parcel_id(self, parcel_id: str) -> Any:
        """Locate the legacy task object associated with one parcel identifier."""
        for task in [*self._carry_tasks, *self._tasks]:
            if str(getattr(task, "num")) == parcel_id:
                return task
        raise KeyError(f"Unknown parcel_id {parcel_id!r}.")
