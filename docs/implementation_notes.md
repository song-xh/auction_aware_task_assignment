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

The older duplicate runner path in `MyMethod/Auction_Framework_Chengdu.py` has been reduced to a compatibility wrapper that forwards to `capa.experiments`.

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

## 7. Scope intentionally excluded from Phase 4

The following are not implemented in this phase:

- RL-CAPA
- DDQN
- replay buffer
- target network
- RL training or evaluation loops
- [17] baselines
- RamCOM / MRA experiments

These remain for later phases.

## 8. Chengdu experiment adapter assumptions

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
