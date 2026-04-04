# Phase 4 Implementation Notes

This document records the explicit implementation choices used for the repaired Phase 4 CAPA code path and the reusable Chengdu environment package.

## 1. New Phase 4 code path

Phase 4 does not extend `MyMethod/Auction_Framework_Chengdu.py`.

Instead, the repaired CAPA implementation lives in:

- `capa/models.py`
- `capa/travel.py`
- `capa/utility.py`
- `capa/cama.py`
- `capa/dapa.py`
- `capa/metrics.py`
- `capa/runner.py`

This keeps CAPA logic reusable for later RL-CAPA work and testable without the Chengdu globals.

The Chengdu environment integration now lives in:

- `env/chengdu.py`
- `env/__init__.py`

The older duplicate runner path in `MyMethod/Auction_Framework_Chengdu.py` and the stale `refactor/` copies have been removed from the executable code path.

## 2. Eq.1 interpretation

The paper markdown around Eq.1 is noisy, but the following elements are stable from the text and examples:

- `B_F(c_P^i, τ) = p_min + (alpha * Delta_d_tau + beta * g(c_P^i)) * gamma * p'_tau`
- `p'_tau = mu_1 * p_tau`
- `gamma` in Eq.1 is the sharing rate of the cooperating platform
- `p_min` is a basic price controlled by the cooperating platform

Phase 4 therefore implements Eq.1 as:

- `p_min` -> `CooperatingPlatform.base_price`
- `gamma` -> `CooperatingPlatform.sharing_rate_gamma`
- `g(c_P^i)` -> `Courier.service_score`
- `alpha`, `beta` -> `Courier.alpha`, `Courier.beta`

The detour term for Eq.1 follows the text immediately below Eq.1:

- `Delta_d_tau = 1 - d(l_k,l_{k+1}) / (d(l_k,l_tau) + d(l_tau,l_{k+1}))`

This is intentionally different from Eq.6's local detour ratio.

## 3. Eq.5 interpretation

Eq.5 is truncated in the markdown extraction.

Phase 4 uses Definition 4 as the authoritative source:

- local assignment revenue: `p_tau - Rc(tau, c_i)`
- cross-platform revenue: `p_tau - p'(tau, c_j)`
- local courier payment: `Rc(tau, c) = zeta * p_tau`

Accordingly:

- local assignment revenue is `fare - zeta * fare`
- cross assignment revenue is `fare - platform_payment`
- cooperating platform revenue is `platform_payment - courier_payment`
- courier revenue is `courier_payment`

## 4. Upper payment limit P_lim

The paper text explains that RVA payments must not exceed `P_lim(tau)`, but the formula is not rendered explicitly in the markdown.

Phase 4 infers:

- `P_lim(tau) = (mu_1 + mu_2) * p_tau`

Reason:

- Example 3 uses `p_tau = 10`, `mu_1 = 0.5`, `mu_2 = 0.4`
- the example states:
  - first-tier FPSA maximum fare is `5.0`
  - upper payment limit is `9.0`
- this matches `(0.5 + 0.4) * 10 = 9.0`

This interpretation is used in `capa.dapa.compute_platform_payment_limit`.

## 5. Batch carry-over and terminal flush

Algorithm 1 line 11 suggests a full reset after each batch, but the paragraph under Algorithm 2 states:

- parcels not allocated in the current batch reenter the next batch for re-matching

Phase 4 follows the prose requirement:

- unresolved parcels after DAPA are carried into the next batch

In addition, the paper pseudocode does not explicitly describe what happens if the timeline ends with a partially filled batch.

Phase 4 performs a final flush:

- any residual batch buffer is processed once at the terminal time

Without this flush, tail parcels would be dropped silently.

## 6. Generic travel model instead of Chengdu graph globals

Phase 4 introduces `DistanceMatrixTravelModel` rather than binding CAPA to `GraphUtils_ChengDu.py`.

This is intentional:

- it removes hidden global state
- it makes unit tests deterministic
- it keeps CAPA reusable for future RL environments

The old Chengdu graph stack can later be adapted into the `capa.travel` interface if needed.

## 7. [17] baseline adaptation notes

The repository now includes baseline runners for:

- Greedy via the original legacy `Framework_ChengDu.Greedy`
- BaseGTA via `baselines.gta.run_basegta_baseline_environment`
- ImpGTA via `baselines.gta.run_impgta_baseline_environment`

Two adaptation boundaries remain explicit:

- The Chengdu environment only contains the local platform's incoming parcel stream. It does not expose separate real task streams for each cooperating platform. Therefore ImpGTA evaluates outer-platform future demand against an empty predicted set rather than a real per-platform forecast.
- The [17] paper varies `Δτ` over `1, 3, 5, 10, 15` minutes, but the markdown extraction does not preserve a single explicit default. This repository uses `180` seconds as the default ImpGTA window and exposes it as a parameter.

## 8. RL-CAPA implementation boundary

RL-CAPA is now implemented in:

- `rl_capa/env.py`
- `rl_capa/ddqn/networks.py`
- `rl_capa/ddqn/replay_buffer.py`
- `rl_capa/ddqn/agent.py`
- `rl_capa/train.py`
- `rl_capa/evaluate.py`
- `algorithms/rl_capa_runner.py`

The unified root `runner.py` can now launch `rl-capa` without fallback.

The current implementation follows the paper and `docs/rl_capa_algo.md` as follows:

- `M_b` selects a discrete batch duration from `A_b = [h_L, ..., h_M]`
- `M_m` only acts on the CAMA output `L_cr`
- CAMA and DAPA themselves are reused unchanged from the heuristic CAPA modules
- both DDQN agents use online Q-networks, target Q-networks, replay buffers, epsilon-greedy exploration, and hard target updates
- joint training uses RMSprop, learning rate `0.001`, and discount factor `0.9`

One explicit implementation choice remains:

- for `a_m = 0` defer decisions, the reward is not guessed immediately
- instead, the transition is resolved at the next batch boundary
- if the parcel reappears in the next auction pool, the stored transition receives `r_m = 0` and a non-terminal next state
- if it is locally assigned before reappearing, the stored transition receives the realized local revenue and terminates
- if the episode ends first, the stored transition terminates with reward `0`

This keeps the reward timing aligned with the paper's delayed-outcome semantics without inventing a heuristic shortcut.

## 8.1 Unified experiment-suite presets

The root `runner.py` now supports:

- `run`
- `sweep`
- `compare`
- `suite`

For `suite`, the repository currently defines the `paper-main` suite with two presets:

- `smoke`
- `chengdu-formal`

`chengdu-formal` is the current official preset for the Chengdu-backed environment. It is not presented as a direct reproduction of Table 2's NYTaxi or Synthetic parameter scales. Instead, it is the current Chengdu-adapted preset that remains operational under the repository's legacy environment builder while still exercising the same paper-facing axes:

- parcel count
- courier count
- cooperating platform count
- batch size

This distinction is intentional and explicit: the paper's original datasets and scales are not identical to the current Chengdu environment path.

## 9. Chengdu experiment adapter assumptions

The official Chengdu experiment path in `capa.experiments` now runs through the reusable `env.chengdu` package, which in turn binds to the repository's legacy simulation environment instead of synthesizing couriers from parcel nodes.

Specifically:

- station generation comes from `Framework_ChengDu.GenerateStation`
- seeded courier schedules come from `Framework_ChengDu.GenerateOriginSchedule`
- courier movement comes from `Framework_ChengDu.WalkAlongRoute`
- CAPA only replaces the assignment decision logic inside the batch loop
- travel distance still comes from the actual Chengdu road graph through `GraphUtils_ChengDu`

The runner now also drains the simulation after the final batch window:

- accepted parcels are not counted as completed until the environment has advanced until all accepted routes are empty
- `CR` is therefore based on delivered parcels, not merely matched parcels
- `TR` and `BPT` remain assignment-stage metrics as in Phase 4

Batch-level experiment curves follow the same rule:

- `cr_over_batches.png` uses each batch's cumulative delivered count
- it no longer uses cumulative accepted assignments as a surrogate for completion

One ambiguity remains:

- the repository does not include a separate real-world cross-platform courier dataset

To keep the base simulation model consistent, the current Chengdu runner seeds one larger legacy courier pool from the original framework and partitions that pool into the local platform plus cooperating platforms.

This preserves:

- real task locations
- real station anchors
- seeded initial courier routes
- time-stepped road-network movement
- route-buffer insertion semantics

But it does not prove that the cooperating platforms correspond to distinct real operators in the source data. That limitation remains documented here rather than hidden behind a synthetic environment.

## 10. CAPA batch-boundary execution and cache layers

The Chengdu CAPA runner now executes one decision epoch per batch boundary.

Concretely, `env.chengdu.run_time_stepped_chengdu_batches()` now follows this sequence for each batch:

- advance the legacy simulation to the batch deadline using the original road-network movement logic
- collect the entire batch parcel set plus the carried backlog from prior batches
- drop only parcels whose deadlines have already expired at the batch deadline
- run `CAMA` once over the whole local batch
- run `DAPA` once over the unresolved remainder
- carry unresolved but still-feasible parcels into the next batch

It no longer performs repeated matching loops inside the same batch window. This matches the paper's batch semantics more closely and avoids the old distortion where `step_seconds` could exceed the batch duration.

This refactor also adds three reusable performance layers used by CAPA and the reusable baseline helpers:

- a distance-only Chengdu graph API for cases that only need shortest-path length rather than a full path reconstruction
- an insertion-result cache keyed by courier route signature and parcel location
- a legacy courier snapshot cache keyed by the mutable legacy route state

The newer geo/batch optimization layer now sits on top of those cache primitives:

- `GeoIndex` stores node-to-coordinate lookups for the Chengdu graph and applies Haversine lower-bound pruning before exact routing
- `BatchDistanceMatrix` is now a directed cache, not a symmetric matrix
- batch warmup is limited to insertion-search pairs only:
  - route-segment base edges
  - route-node to parcel
  - parcel to route-node

This is deliberate. The Chengdu road graph is directional, so mirroring `a -> b` into `b -> a` would be incorrect. Likewise, a full all-pairs warmup over every active node in a large batch is too expensive and is not required by insertion search.

These caches are intentionally transparent:

- they do not change feasibility, bids, or rewards
- they only avoid recomputing repeated route-projection and insertion-search results within a stable route state

The formal runner path now uses the same optimization context as the ad-hoc experiment helpers:

- `ChengduEnvironment` carries `geo_index` and `travel_speed_m_per_s`
- environment seeding and cloning preserve that context for `compare`, `sweep`, and `suite`
- the unified CAPA runner passes it into the batch runner
- baseline runners read the same environment-level context instead of rebuilding private optimization state

One explicit safety rule remains:

- if the final batch still has carried backlog and no courier routes remain pending, the unresolved backlog is marked terminal instead of being retried forever

This is not fallback logic. It is the terminal condition for parcels that are no longer schedulable under the current environment state.

## 10. Service-radius interpretation

The paper varies courier service radius `rad` in Table 2 and Exp-3, but it does not provide a formal equation for how `rad` enters the feasibility checks.

The current repository therefore makes one explicit inference from the experimental text:

- `service_radius` is interpreted as the maximum shortest-path distance from a courier's current location to a pick-up parcel location

This interpretation is motivated by the paper's explanation that enlarging `rad` lets couriers "access and fulfill more requests", which is most directly modeled as a courier-to-task reachability bound.

The unified Chengdu implementation now applies this inference consistently across:

- CAPA local matching feasibility
- CAPA cross-platform bidding feasibility
- Greedy candidate filtering
- BaseGTA / ImpGTA idle-worker feasibility

This is deliberately implemented as one shared constraint rather than separate heuristics for each algorithm.

Important boundary:

- this is a paper-guided inference from the experimental section, not a formula explicitly rendered in the manuscript

It is still more paper-faithful than the previous state, where `rad` was not modeled at all.

## 11. Revenue-accounting audit

The paper's explicit local-platform revenue definition is given in Definition 4 and Eq. 5:

- local completion: `p_tau - Rc(tau, c)`
- cross-platform completion: `p_tau - p'(tau, c)`
- the manuscript simplifies `Rc(tau, c)` to the fixed ratio `zeta * p_tau`

During the April 1 audit, no explicit formula was found that directly decays platform revenue as a function of parcel waiting time or "placement time". The paper discusses courier/platform incentives, deferred matching, and high-value parcel prioritization, but the rendered revenue formula remains the net-payment form above.

Accordingly, the repository now uses the following paper-faithful interpretation:

- CAPA keeps its existing Eq. 5 accounting
- BaseGTA / ImpGTA local completions are evaluated with `p_tau - zeta * p_tau`
- BaseGTA / ImpGTA cross-platform completions are evaluated with `p_tau - payment_to_winning_platform`
- MRA local completions are evaluated with `p_tau - zeta * p_tau`
- RamCOM local completions are evaluated with `p_tau - zeta * p_tau`
- RamCOM cross-platform completions are evaluated with `p_tau - outer_payment`

This change fixes an earlier inconsistency where some baselines reported:

- raw parcel fare
- `fare - dispatch_cost`
- or other source-paper-specific utility terms

instead of the CPUL paper's local-platform net revenue.

The repository now enforces the same Eq. 5 local-platform revenue accounting for:

- CAPA
- Greedy
- BaseGTA
- ImpGTA
- MRA
- RamCOM

`Greedy` was originally delegated to the legacy Chengdu framework, which only exposed aggregate printed revenue. It is now evaluated through the unified Chengdu environment and settles each accepted local completion as `p_tau - zeta * p_tau`, matching CAPA's metric surface.

One explicit non-change is also important:

- no additional waiting-time or placement-time decay term is applied to experimental TR

During the paper audit, no standalone formula was found that directly modifies experimental platform revenue by a temporal decay factor. The paper discusses delayed matching, task prioritization, and RL discounting over future rewards, but the rendered experimental TR definition remains Eq. 5 net revenue. Therefore the repository does not invent an extra decay heuristic beyond the paper's explicit payment-based formulation.
