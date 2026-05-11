# Deadline-Handling Code Review (2026-05-11)

## Scope

Audit whether RL-CAPA, CAPA, and every baseline compute TR/CR under the paper rule:
**parcel revenue counts only when the courier arrives at `l_τ` before pickup deadline `t_τ`**
(Definition 2 + Deadline Constraint, *Auction-Aware Crowdsourced Parcel Assignment*).

Paper objective (Eq.5) is realised revenue, conditioned on the deadline constraint of Sec. III-B.

## TL;DR

| Path | Deadline-conditioned TR | Deadline-conditioned CR | Status |
|---|---|---|---|
| Greedy (`baselines/greedy.py`) | yes | yes | OK |
| BaseGTA / ImpGTA (`baselines/gta.py`) | yes | yes | OK |
| MRA (`baselines/mra.py`) | yes | yes | OK |
| RamCOM (`baselines/ramcom.py`) | yes | yes | OK |
| CAPA via Chengdu (`env/chengdu.run_time_stepped_chengdu_batches`) | yes | yes | OK |
| CAPA standalone (`capa/runner.run_capa`) | **NO** (accepted revenue, not delivered) | **NO** | BUG |
| RL-CAPA evaluation (`rl_capa/evaluate_core.py`) | yes | yes | OK |
| **RL-CAPA reward `R_t`** (`rl_capa/env.py`) | **NO** (accepted revenue, not delivered) | n/a | BUG — trains on wrong signal |
| CAMA / DAPA decision-time deadline gate | partial (single-leg from `current_location`) | n/a | WEAKNESS |

Final paper-comparable TR/CR numbers are computed correctly for every entry point that runs the movement simulator. The two real defects are:

1. **RL reward is not deadline-aware**: π1/π2 are optimised against revenue at the moment of CAMA/DAPA acceptance, not against the on-time delivered revenue the paper rewards.
2. **CAMA/DAPA decision-time feasibility ignores already-queued stops**: a courier with a long pending route may be admitted even though it cannot actually reach `l_τ` before `t_τ` after prior tasks. The execution-time deadline accounting still classifies these as timed-out, so the reported TR/CR are not inflated, but the algorithm wastes capacity on objectively infeasible matches.

Details below.

---

## 1. Paper rule (authoritative)

* Def. 2: `τ = (l_τ, t_τ, w_τ, p_τ)` — `t_τ` is the **pick-up deadline**.
* Deadline constraint (Sec. III-B): `c` must arrive at `l_τ` and at `l_ψ` before both parcel deadlines and courier deadline.
* Objective is total realised revenue for completed parcels (Eq.5); a parcel whose deadline is missed is by definition not "completed", so it must contribute 0 to both TR and CR.

## 2. Simulator semantics

`Framework_ChengDu.WalkAlongRoute` emits `delivery_events[{task_id, completed_at, deadline}]` when the courier reaches `re_schedule[0].l_node` (i.e., the parcel pick-up location) — see `Framework_ChengDu.py:308-316,335-343`. So `completed_at` = wall-clock the courier arrives at `l_τ`, and `deadline = task.d_time = t_τ`.

`env/chengdu.py` consumes these events:

* `advance_legacy_routes_with_deadline_accounting` (`env/chengdu.py:1044-1126`): for every removed-from-route task, builds `DeliveryOutcome(on_time = completed_at <= deadline)` and adds it to either `delivered_task_ids` or `timed_out_task_ids`. Deadline uses `get_true_deadline(task)` (= `d_time`), independent of any model-side `observed_d_time` (`env/chengdu.py:408-433`). This is the right reference point for paper TR/CR.

## 3. Baselines — correct

All baselines accumulate `accepted_revenues_by_task_id` at acceptance time, then realise revenue only for `delivered_task_ids` via `sum_delivered_assignment_revenue` (`baselines/common.py:33-54`), and CR uses `len(delivered_task_ids) / total_tasks`.

| File | TR site | CR site |
|---|---|---|
| `baselines/greedy.py:253-258` | `sum_delivered_assignment_revenue(accepted_revenues_by_task_id, delivered_task_ids)` | `delivered_parcels / total_tasks` |
| `baselines/gta.py:808-818` | same | `delivered_parcels / total_task_count` |
| `baselines/mra.py:287-292` | same | same |
| `baselines/ramcom.py:486-506` | same | same |

Decision-time deadline gates: each baseline calls `is_deadline_feasible_by_geo` plus an exact `arrival_time <= deadline` check (e.g., `baselines/gta.py:147-166`). GTA's `find_best_legacy_insertion_option` (`baselines/gta.py:141-214`) builds the insertion candidate from the previous stop's `reach_time`, so the deadline check incorporates queued stops. MRA/RamCOM reach the same constraint via `build_legacy_feasible_insertions` → `is_feasible_local_match`.

After scheduling, every baseline drives the route via `advance_legacy_routes_with_deadline_accounting` and a final `drain_legacy_routes_with_deadline_accounting`, so missed-deadline parcels are excluded from TR/CR even when the planner over-promised.

**Conclusion**: baselines match the paper rule.

## 4. CAPA — split implementation

### 4.a Chengdu pipeline (`run_time_stepped_chengdu_batches` in `env/chengdu.py:1885+`) — correct

Final metrics (`env/chengdu.py:2088-2103`):

```python
delivered_parcels   = finalize_chengdu_runtime(runtime)
delivered_assignments = delivered_assignments_from_runtime(runtime)
timed_out_assignments = timed_out_assignments_from_runtime(runtime)
metrics = build_run_metrics(
    delivered_assignments,            # ← TR only over delivered
    len(tasks),
    runtime.batch_reports,
    delivered_parcel_count=len(delivered_parcels),  # ← CR uses delivered
    accepted_parcel_count=len(runtime.matching_plan),
    timed_out_parcel_count=len(timed_out_assignments),
)
```

`compute_total_revenue` then sums `local_platform_revenue` over `delivered_assignments` only (`capa/metrics.py:10-12`, called with the filtered list). This is the path used by `capa/experiments.run_chengdu_experiment` and by RL-CAPA training/evaluation runners. **OK.**

### 4.b Pure runner (`capa.runner.run_capa`) — bug

`capa/runner.py:127-132`:

```python
return CAPAResult(
    matching_plan=matching_plan,
    ...
    metrics=build_run_metrics(matching_plan, len(parcels), batch_reports),
)
```

* `matching_plan` is the **accepted** plan, never trimmed by realised on-time delivery.
* No `delivered_parcel_count` is supplied, so `compute_completion_rate` reduces to `len(matching_plan) / total_parcels` — counts *accepted*, not *delivered* (`capa/metrics.py:38, 42`).
* No movement simulator is invoked, so there is no `timed_out_assignment_ids` either.

This path is used by tests and any caller that bypasses the Chengdu wrapper. Numbers reported here are **promised TR/CR**, not paper-conformant TR/CR, and silently inflate revenue and completion versus the on-time semantics expected by the paper.

### 4.c CAMA/DAPA decision-time feasibility — weakness, not a TR/CR bug

`capa/cama.py:27-50` and `capa/dapa.py:30-55` both use:

```python
arrival_time = now + travel_model.travel_time(courier.current_location, parcel.location)
return arrival_time <= parcel.deadline
```

i.e., a single-leg check from the courier's *current* location, ignoring any pickups already queued in `courier.route_locations`. `find_best_local_insertion` (`capa/utility.py:444-493`) selects the best Eq.6 ratio without re-validating per-insertion deadlines.

Impact:

* For couriers with a non-trivial pending route, the gate is **over-permissive** — a parcel can be accepted that physically cannot be reached in time after preceding stops. Execution-time accounting (Sec. 4.a) then routes it to `timed_out_assignment_ids`, so reported TR/CR remain correct.
* But the courier's capacity/route is consumed for a parcel that yields no revenue and possibly blocks a parcel that could have been delivered. The objective therefore suffers without showing up as a metric correctness issue.

Recommended fix: tighten `is_feasible_local_match` / `is_feasible_cross_candidate` to run the deadline check from the insertion predecessor's `reach_time`, the way GTA's `find_best_legacy_insertion_option` does.

## 5. RL-CAPA

### 5.a Evaluation — correct

`rl_capa/evaluate_core.py:107-118`:

```python
delivered_assignments = env.delivered_assignments()
delivered_parcels     = env.delivered_parcels()
total_revenue   = sum(a.local_platform_revenue for a in delivered_assignments)
completion_rate = len(delivered_parcels) / max(total_parcels, 1)
```

Paper-aligned. `EvalResult.total_revenue` / `EvalResult.completion_rate` reported in `rl_capa/evaluate.py:71-72` come from this code path.

### 5.b Reward `R_t` — bug

`rl_capa/env.py:283`:

```python
step_revenue = compute_total_revenue([*local_assignments, *cross_assignments])
self._clear_current_batch_state()
return step_revenue
```

`apply_stage2_decisions` and `apply_capa_batch` (`rl_capa/env.py:212-285, 292-362`) both return `compute_total_revenue` over the freshly **accepted** local+cross assignments. `compute_total_revenue` sums every accepted `local_platform_revenue` unconditionally (`capa/metrics.py:10-12`).

Consumers:

* `rl_capa/stage2_trainer.py:175,180` — sets `record.reward = self.env.apply_stage2_decisions(...)`.
* `rl_capa/stage1_trainer.py:177` — sets `reward = self.env.apply_capa_batch()`.
* `rl_capa/trainer.py:374, 384` — same pattern in the joint trainer.

All three trainers then compute returns and advantages from these per-step accepted-revenue rewards (`stage2_trainer.py:123-126`, `trainer.py:402-453`).

Consequence: π1, π2, V1, V2 are trained against
$$\tilde R_t = \sum_{i \in B_t^{\text{accepted}}} \text{rev}(i),$$
not against the paper's
$$R_t = \sum_{i \in B_t^{\text{on-time}}} \text{rev}(i) = \tilde R_t - \sum_{i \in B_t^{\text{timed-out}}} \text{rev}(i).$$

Specifically:

* π1 (batch-size actor) is rewarded for selecting batches that maximise *promised* fare. If a smaller batch keeps more couriers on-time and a larger batch over-promises, the gradient still favours the larger batch.
* π2 (cross-or-not actor) is rewarded equally for a local match that will time out and a local match that will deliver. The reward never discounts an assignment whose `arrival_time > t_τ` would have been caught at execution.
* V1 / V2 fit to this same shifted target.

Evaluation reports the right numbers, so the issue is invisible in training logs that print `EvalResult.total_revenue`, but the policy is being optimised toward a related-but-different objective. Empirically expect the trained policy to over-commit local couriers and tolerate timed-out matches.

Recommended fix — make the reward equal to *realised* delivered revenue per batch. Options, in increasing fidelity:

1. **Cheapest**: after `finalize_chengdu_batch`, walk the freshly-emitted `runtime.delivery_outcomes` for the current step window and rebuild `step_revenue` from `delivered_assignments` minted in this batch only. The runtime already stores `delivered_assignment_ids` / `timed_out_assignment_ids` and the movement callback emits per-event `completed_at`, so this is bookkeeping, not new simulation.
2. **More aggressive**: penalise timed-out acceptance directly, e.g. `reward = delivered_revenue_t − λ · timed_out_revenue_t`, to disincentivise over-promising even before delivery.
3. **Cleanest**: switch the per-step reward to terminal-credited delivered revenue using GAE/Monte-Carlo over the deadline-resolved episode trace — minimal compute but requires re-aligning the per-step buffers to delivery times.

Whichever variant is used, the same change has to be applied in `rl_capa/env.py:283` *and* `rl_capa/env.py:360` (`apply_capa_batch`) so π1's CAPA-baseline branch trains on the same signal.

### 5.c State features — informational

`build_stage1_state` uses `delivered_ratio = len(matching_plan)/total_parcels` and `expired_ratio = len(terminal_unassigned)/total_parcels` (`rl_capa/env.py:139-151`). `matching_plan` counts *accepted* parcels, so "delivered_ratio" misnames `accepted_ratio` here — not a TR/CR bug, but the agent observes a feature whose semantics drift from delivered-on-time.

## 6. Minor — `observed_d_time` vs `true_d_time`

`env/chengdu.legacy_task_to_parcel(..., use_observed_deadline=True)` (`env/chengdu.py:707-725`) exposes `observed_d_time` to planners while `get_true_deadline` keeps `d_time` for accounting. If `observed_d_time != d_time` in any data path, a planner can intentionally promise based on the observed value and the metric will charge it against the true value. Currently both equal the original `d_time`; flag for vigilance if ever decoupled for robustness experiments.

## 7. Action items, in priority order

1. **Make RL-CAPA reward deadline-aware** (`rl_capa/env.py:283, 360`). Without this, π1/π2 are trained on the wrong objective and any reported RL-vs-CAPA gap is biased.
2. **Fix `capa/runner.run_capa` standalone metrics** to use delivered semantics, or document that its TR/CR are "promised" and forbid its use for paper comparisons.
3. **Tighten CAMA/DAPA decision-time deadline check** to honour predecessor `reach_time`, matching GTA's behaviour. No metric impact, but improves CAPA's actual delivered TR.
4. Rename `delivered_ratio`/`expired_ratio` features in stage-1 state (or recompute against `delivered_assignment_ids` / `timed_out_assignment_ids` so the name is accurate).
