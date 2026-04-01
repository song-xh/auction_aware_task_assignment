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

## 8. Scope intentionally excluded from the current codebase

The following are still not implemented:

- RL-CAPA
- DDQN
- replay buffer
- target network
- RL training or evaluation loops
- RamCOM / MRA experiments

These remain for later phases.

The unified root `runner.py` now registers `rl-capa` explicitly but does not emulate it:

- selecting `--algorithm rl-capa` raises a clear not-implemented error
- there is no fallback to `capa`

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

One remaining boundary still exists:

- the current `Greedy` baseline is delegated to the legacy Chengdu framework, which only exposes aggregate printed revenue rather than per-assignment settlement records

So the corrected Eq. 5 accounting is fully enforced for the maintained Python baselines (`BaseGTA`, `ImpGTA`, `MRA`, `RamCOM`) and CAPA, while legacy `Greedy` still follows the original framework's aggregate output unless that runner is fully reimplemented inside the unified environment.
