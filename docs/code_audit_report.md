# Code Audit Report

Phase 3 audit for `docs/agent.md` Objective A.

Scope:

- paper source of truth: `docs/Auction-Aware_Crowdsourced_Parcel_Assignment_for_Cooperative_Urban_Logistics.md`
- reference [17]: `docs/MinerU_markdown_Competition_and_Cooperation_Global_Task_Assignment_in_Spatial_Crowdsourcing_2039180845507551232.md`
- Phase 1 extraction: `docs/paper_spec_checklist.md`
- Phase 2 repository inspection: `docs/repository_structure_inspection_notes.md`

Audit rule:

- the paper is authoritative
- the current repository is treated as an incomplete and partially inconsistent draft
- this phase does not modify code

## 1. File Mapping Table

| Paper module | Source file(s) | Audit status |
| --- | --- | --- |
| CAMA | `MyMethod/Auction_Framework_Chengdu.py` (`enumerate_candidates`, `compute_utility`, `compute_threshold`, `_local_phase_step`) | `⚠️ 部分实现` |
| DAPA / DLAM | `MyMethod/Auction_Framework_Chengdu.py` (`_courier_bid_fpsa`, `internal_fpsa_for_platform`, `platform_bid_rva`, `_cross_phase_step`) | `⚠️ 部分实现` |
| CAPA runner | `MyMethod/Auction_Framework_Chengdu.py` (`make_batches_by_time`, `run_multiplatform_time_stepped`, `main`) | `⚠️ 部分实现` |
| RL-env | `❌ 未找到` | `❌ 缺失` |
| DDQN | `❌ 未找到` | `❌ 缺失` |
| Training | `❌ 未找到` | `❌ 缺失` |
| Evaluation | `❌ 未找到` | `❌ 缺失` |
| Data loading | `Tasks_ChengDu.py`, `GraphUtils_ChengDu.py`, `refactor/data.py`, `refactor/graph.py` | `⚠️ 与论文模块解耦，存在重复实现` |
| Legacy / baseline runner | `Framework_ChengDu.py`, `MethodUtils_ChengDu.py`, `refactor/framework.py`, `refactor/algorithm.py`, `refactor/method_utils.py` | `⚠️ 旧逻辑，不对应论文 CAPA/RL-CAPA 主线` |

High-level conclusion:

- the only file that materially overlaps with the paper's CAPA pipeline is `MyMethod/Auction_Framework_Chengdu.py`
- no executable RL-CAPA implementation exists anywhere in the repository

## 2. CAPA Completeness Audit

### 2.1 Algorithm 1: CAPA

| Line | Paper step | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Initialize `M <- empty`, `Gamma_S <- empty`, `t_cum = 0` | `⚠️` | `run_multiplatform_time_stepped()` initializes counters and `unassigned`, but no explicit `M`, `Gamma_S`, `t_cum` state (`MyMethod/Auction_Framework_Chengdu.py:827-845`) |
| 2 | `while` timeline not terminal | `⚠️` | Implemented as a loop over pre-bucketed batches and intra-batch steps, not the paper's stream loop (`MyMethod/Auction_Framework_Chengdu.py:851-895`) |
| 3 | Retrieve arriving parcels `Gamma_t` | `⚠️` | `arrived = [t for t in unassigned if s_time <= t0]` (`MyMethod/Auction_Framework_Chengdu.py:853-856`) |
| 4 | `Gamma_S <- Gamma_S union Gamma_t` | `⚠️` | Implicit in `unassigned` and `arrived`; no explicit buffer state |
| 5 | Trigger when `t_cum == Delta_b` | `🔧` | `make_batches_by_time()` pre-buckets tasks using fixed `BATCH_SECONDS`; no online `t_cum` trigger (`MyMethod/Auction_Framework_Chengdu.py:558-569`, `MyMethod/config.py:13`) |
| 6 | Retrieve local couriers `C_S` | `✅` | `couriers_local = [ic.ref for ic in local_platform.couriers]` (`MyMethod/Auction_Framework_Chengdu.py:829-831`) |
| 7 | Retrieve cooperating platforms `P_S` | `✅` | `partners` passed into runner and used in cross phase (`MyMethod/Auction_Framework_Chengdu.py:832-835`, `878-881`) |
| 8 | Run CAMA | `⚠️` | `_local_phase_step()` is the nearest implementation, but diverges from Algorithm 2 control flow (`MyMethod/Auction_Framework_Chengdu.py:574-615`) |
| 9 | Run DAPA | `⚠️` | `_cross_phase_step()` exists, but diverges from Algorithm 3 bidding and settlement logic (`MyMethod/Auction_Framework_Chengdu.py:620-657`) |
| 10 | `M <- M union M_lo union M_cr` | `⚠️` | Counts and revenues are accumulated, but no explicit matching plan object is produced (`MyMethod/Auction_Framework_Chengdu.py:870-887`, `903-930`) |
| 11 | Reset `M_cr`, `M_lo`, `Gamma_t`, `t_cum` | `⚠️` | Reset is only implicit through local scope and next iteration; no paper-style reset block |
| 12 | Return `M` | `❌` | Runner returns nothing; only prints metrics and updates `sink` (`MyMethod/Auction_Framework_Chengdu.py:827-932`) |

Algorithm 1 verdict:

- CAPA exists only as a partial heuristic runner
- the repository does not contain a paper-faithful standalone CAPA implementation

### 2.2 Algorithm 2: CAMA

| Line | Paper step | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Initialize `M_lo`, `L_cr`, `M_t`, `G` | `⚠️` | `_local_phase_step()` initializes local containers, but not the paper's exact sets (`MyMethod/Auction_Framework_Chengdu.py:574-578`) |
| 2 | For each parcel `tau_i in Gamma_t` | `✅` | `enumerate_candidates()` iterates tasks (`MyMethod/Auction_Framework_Chengdu.py:223-236`) |
| 3 | `S_tau <- empty` | `❌` | No explicit per-task candidate set exists |
| 4 | For each courier `c_j in C_S` | `✅` | Candidate courier loop exists (`MyMethod/Auction_Framework_Chengdu.py:224-225`) |
| 5 | Deadline and capacity feasibility check | `✅` | Capacity and deadline are checked before utility computation (`MyMethod/Auction_Framework_Chengdu.py:226-235`) |
| 6 | Compute `u(tau_i, c_j)` | `✅` | `compute_utility()` called during candidate enumeration (`MyMethod/Auction_Framework_Chengdu.py:231`) |
| 7 | Insert tuple into `S_tau` | `⚠️` | Tuples go into global `cands`, not explicit `S_tau` (`MyMethod/Auction_Framework_Chengdu.py:236`) |
| 8 | If `|S_tau| != 0` | `⚠️` | Handled implicitly by whether a task yielded any candidate tuples |
| 9 | `M_t <- M_t union S_tau` | `⚠️` | Candidate universe exists but is not materialized as paper-defined `M_t` |
| 10 | Choose `arg max u(tau_i,c_j)` from `S_tau` | `❌` | Current implementation runs global KM or global greedy over all pairs, not per-task best-pair selection (`MyMethod/Auction_Framework_Chengdu.py:593-598`) |
| 11 | `G <- G union {(tau_i,c_j,u)}` | `❌` | No explicit best-pair set `G` |
| 12 | Else branch for infeasible parcel | `⚠️` | No direct line-level append; infeasible tasks simply do not produce candidates |
| 13 | `L_cr <- L_cr union {tau_i}` | `⚠️` | Later inferred through `remaining_tasks` / `cross_candidates`, not constructed at this step (`MyMethod/Auction_Framework_Chengdu.py:606-615`, `875-876`) |
| 14 | Compute threshold `T_h` on `M_t` by Eq.7 | `🔧` | `compute_threshold()` uses only final matched pairs, not full `M_t` (`MyMethod/Auction_Framework_Chengdu.py:326-333`) |
| 15 | For each tuple in `G` | `🔧` | `split_local_or_cross()` iterates final matched pairs, not `G` (`MyMethod/Auction_Framework_Chengdu.py:336-345`) |
| 16 | If `u >= T_h` | `✅` | Threshold comparison is implemented (`MyMethod/Auction_Framework_Chengdu.py:339-344`) |
| 17 | `M_lo <- M_lo union {(tau_i,c_j)}` | `✅` | Local assignments are inserted into schedules (`MyMethod/Auction_Framework_Chengdu.py:348-360`) |
| 18 | Else | `✅` | Low-utility pairs are sent to the cross set via `cross_list` |
| 19 | `L_cr <- L_cr union {tau_i}` | `✅` | Remaining tasks become cross candidates (`MyMethod/Auction_Framework_Chengdu.py:600-615`, `875-876`) |
| 20 | Return `M_lo, L_cr` | `⚠️` | `_local_phase_step()` returns landed local pairs and remaining tasks, not exact paper sets (`MyMethod/Auction_Framework_Chengdu.py:615`) |

Algorithm 2 verdict:

- the feasibility and utility core exists
- the set construction logic `S_tau`, `M_t`, `G` is missing
- the threshold is computed on the wrong universe

### 2.3 Algorithm 3: DAPA

| Line | Paper step | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Initialize `M_cr <- empty` | `⚠️` | `_cross_phase_step()` initializes counters and lists, but no explicit `M_cr` set (`MyMethod/Auction_Framework_Chengdu.py:627-630`) |
| 2 | For each cross parcel `tau_i in L_cr` | `✅` | Implemented as loop over `remaining_tasks` (`MyMethod/Auction_Framework_Chengdu.py:633-650`) |
| 3 | Step 1: FPSA | `✅` | First-layer bidding exists via `internal_fpsa_for_platform()` |
| 4 | `B_tau_i <- empty` | `⚠️` | Reconstructed implicitly in `platform_bid_rva()` from `all_platform_bids`; not explicit |
| 5 | For each platform `P_j in P_S` | `✅` | Partner loop exists (`MyMethod/Auction_Framework_Chengdu.py:623-626`) |
| 6 | `B_F <- empty` | `⚠️` | Not explicitly stored; only best bid retained |
| 7 | Obtain `C_P_j` | `✅` | `platform.couriers` used (`MyMethod/Auction_Framework_Chengdu.py:494-495`) |
| 8 | For each courier in `C_P_j` | `✅` | Courier loop exists (`MyMethod/Auction_Framework_Chengdu.py:494-498`) |
| 9 | Check validity of `(c, tau_i)` | `🔧` | No explicit deadline/capacity validation in the FPSA layer; `_courier_bid_fpsa()` only rejects unreachable insertions (`MyMethod/Auction_Framework_Chengdu.py:473-483`) |
| 10 | Compute `B_F` by Eq.1 | `🔧` | Formula does not match Eq.1 (`MyMethod/Auction_Framework_Chengdu.py:473-483`) |
| 11 | Insert into `B_F` | `⚠️` | No explicit bid set; running max only |
| 12 | If `B_F` non-empty | `✅` | `if best is not None and best_price > 0` (`MyMethod/Auction_Framework_Chengdu.py:499-500`) |
| 13 | Sort `B_F` descending | `⚠️` | Implemented as running argmax, not explicit sort |
| 14 | Internal winner is top bid | `⚠️` | Correct high-level effect, but only because a running max is tracked |
| 15 | Insert internal winner into `B_tau_i` | `⚠️` | Stored in `out[t.num]`, not in explicit parcel-level set |
| 16 | Step 2: RVA | `✅` | Second-layer bidding exists via `platform_bid_rva()` |
| 17 | If `|B_tau_i| >= 2` | `✅` | `multi = len(bucket) >= 2` (`MyMethod/Auction_Framework_Chengdu.py:518`) |
| 18 | `B_R <- empty` | `✅` | `bids = []` (`MyMethod/Auction_Framework_Chengdu.py:517`) |
| 19 | For each tuple in `B_tau_i` | `✅` | Implemented (`MyMethod/Auction_Framework_Chengdu.py:519-523`) |
| 20 | Compute `B_R(P_j, tau_i)` | `⚠️` | Two-case structure exists, but `f(P)` is static config and no upper-limit filter exists (`MyMethod/Auction_Framework_Chengdu.py:520-523`, `MyMethod/config.py:10`) |
| 21 | Insert into `B_R` | `✅` | Implemented (`MyMethod/Auction_Framework_Chengdu.py:523`) |
| 22 | Sort `B_R` ascending | `✅` | Implemented (`MyMethod/Auction_Framework_Chengdu.py:524`) |
| 23 | Pick winner platform | `✅` | Implemented (`MyMethod/Auction_Framework_Chengdu.py:525`) |
| 24 | Payment is second-lowest platform bid | `✅` | Implemented (`MyMethod/Auction_Framework_Chengdu.py:526`) |
| 25 | `M_cr <- M_cr union {(tau_i, c_Pwin)}` | `✅` | Winning courier receives task (`MyMethod/Auction_Framework_Chengdu.py:636-650`) |
| 26 | If `|B_tau_i| == 1` | `✅` | Single-bidder case handled by `len(bucket) < 2` |
| 27 | Payment is `B_F + mu_2 * p_tau` | `✅` | Implemented at high level in single-bidder branch (`MyMethod/Auction_Framework_Chengdu.py:520-526`) |
| 28 | Add winner pair to `M_cr` | `✅` | Same insertion path as line 25 |
| 29 | Return `M_cr` | `⚠️` | Returns counts, bid lists, assigned tasks; not explicit matching set (`MyMethod/Auction_Framework_Chengdu.py:657`) |

Algorithm 3 verdict:

- the two-layer auction structure exists
- FPSA formula and validity gating are not paper-faithful
- RVA payment rule exists, but surrounding constraints and quality term are incomplete

### 2.4 Eq.1-Eq.7 Implementation Status

| Equation | Paper role | Status | Audit finding |
| --- | --- | --- | --- |
| Eq.1 | FPSA bid | `🔧` | `_courier_bid_fpsa()` uses `THETA_BID * MU_1 * fare * (0.5 + 0.5 * g_score) - cost`; it omits `p_min`, `alpha`, `beta`, and the paper's multiplicative form (`MyMethod/Auction_Framework_Chengdu.py:473-483`) |
| Eq.2 | FPSA winning price | `⚠️` | `internal_fpsa_for_platform()` picks the max first-layer bid, but the underlying bid is already wrong and no paper-validity gate is enforced (`MyMethod/Auction_Framework_Chengdu.py:486-507`) |
| Eq.3 | RVA bid | `⚠️` | `platform_bid_rva()` does distinguish `|P_tau| = 1` vs `>= 2`, but uses static `COOP_QUALITY` instead of `Qbar_P^Loc / T_Loc` and omits upper-limit screening (`MyMethod/Auction_Framework_Chengdu.py:510-527`, `MyMethod/config.py:10`) |
| Eq.4 | RVA payment | `✅` | Second-lowest rule is implemented (`MyMethod/Auction_Framework_Chengdu.py:525-526`) |
| Eq.5 | Revenue function | `🔧` | `settle_cross_platform()` uses `p_tau - MU_1 * p_tau` instead of `p_tau - pay_price` for the local platform's cross revenue; local and partner revenue accounting is not paper-faithful (`MyMethod/Auction_Framework_Chengdu.py:530-538`) |
| Eq.6 | Utility function | `✅` | `compute_utility()` matches `gamma * Delta_w + (1-gamma) * Delta_d` (`MyMethod/Auction_Framework_Chengdu.py:196-202`) |
| Eq.6a | Capacity ratio `Delta_w` | `✅` | `compute_delta_weight()` matches the intended structure (`MyMethod/Auction_Framework_Chengdu.py:190-193`) |
| Eq.6b | Detour ratio `Delta_d` | `✅` | `compute_best_insert_and_detour()` searches insertion points and uses `base / (a + b)` (`MyMethod/Auction_Framework_Chengdu.py:149-187`) |
| Eq.7 | Dynamic threshold | `🔧` | `compute_threshold()` averages utility over matched pairs, not over all potential pairs in `M_t` (`MyMethod/Auction_Framework_Chengdu.py:326-333`) |

CAPA summary:

- correct core: Eq.6
- partial core: Eq.2, Eq.3, Eq.4
- incorrect core: Eq.1, Eq.5, Eq.7

## 3. RL-CAPA Completeness Audit

### 3.1 M_b audit

| Component | Paper definition | Status | Evidence |
| --- | --- | --- | --- |
| `S_b` | `(|Gamma_t^Loc|, |C_t^Loc|, |D|, |T|)` | `❌` | No batch-level RL state builder found in any `.py` file |
| `A_b` | batch-size action set `[h_L, ..., h_M]` | `❌` | Only fixed `BATCH_SECONDS = 10 * 60` exists (`MyMethod/config.py:13`) |
| `R_b` | batch revenue `Rev_S(Gamma_Loc, C_Loc, P)` | `❌` | No RL reward code; only heuristic ledger aggregation exists |
| `P_b` | environment transition | `❌` | No RL environment class or transition function found |

### 3.2 M_m audit

| Component | Paper definition | Status | Evidence |
| --- | --- | --- | --- |
| `S_m` | `(|Delta_Gamma|, t_tau, t_cur, Delta_b)` | `❌` | No parcel-level RL state builder found |
| `A_m` | binary decision `cross` or `defer` | `❌` | Current code uses heuristic threshold split, not RL action selection |
| `R_m` local-success branch | `p_tau - Rc(tau,c)` | `❌` | No RL reward branch exists |
| `R_m` cross-success branch | `p_tau - p'_tau(tau,c)` | `❌` | No RL reward branch exists |
| `R_m` fail / defer branch | `0` | `❌` | No RL reward branch exists |
| `P_m` | parcel-level transition | `❌` | No RL environment found |

### 3.3 DDQN components

Repo-wide search found no `torch`, `tensorflow`, `keras`, `DQN`, `DDQN`, `replay buffer`, `epsilon`, `target network`, or optimizer-backed training code.

| DDQN component | Status | Evidence |
| --- | --- | --- |
| Online Q-network | `❌` | No network definition found |
| Target Q-network | `❌` | No target network found |
| Replay buffer | `❌` | No replay buffer found |
| Epsilon-greedy exploration | `❌` | No epsilon scheduling or exploration policy found |
| Target update | `❌` | No soft or hard update logic found |
| Optimizer step | `❌` | No backprop or optimizer code found |

### 3.4 Joint training loop

| Item | Status | Evidence |
| --- | --- | --- |
| Episode loop | `❌` | No episode-level RL loop found |
| Environment step loop | `❌` | No RL environment found |
| Online optimization step | `❌` | No loss computation or gradient step found |
| Joint `M_b` and `M_m` interaction | `❌` | No executable RL-CAPA implementation exists |

### 3.5 Evaluation loop

| Item | Status | Evidence |
| --- | --- | --- |
| Trained policy evaluation | `❌` | No evaluation runner for RL agents found |
| Checkpoint loading | `❌` | No model serialization or loading code found |
| Reward / loss curve generation | `❌` | `finalize_and_plot()` only plots heuristic counts and revenue (`MyMethod/Auction_Framework_Chengdu.py:935-980`) |

RL-CAPA verdict:

- RL-CAPA is completely absent from the source tree
- the repository currently implements only a partial heuristic CAPA draft

## 4. Missing Logic List

### 4.1 Missing paper modules

- standalone CAPA function that returns the matching plan `M`
- standalone CAMA function with explicit `S_tau`, `M_t`, `G`, `M_lo`, `L_cr`
- standalone DAPA / DLAM function returning `M_cr`
- standalone revenue function matching Eq.5
- paper-defined cooperation quality estimator `f(P) = Qbar_P^Loc / T_Loc`
- upper-limit and payment constraints for cross-platform bidding
- paper-faithful single source of truth for CAPA utilities and constraints

### 4.2 Missing RL-CAPA modules

- RL environment for `M_b`
- RL environment for `M_m`
- DDQN model definition for batch-size selection
- DDQN model definition for cross-or-not parcel decision
- replay buffer
- target network
- epsilon-greedy exploration
- optimization step and training loop
- evaluation loop
- checkpointing
- real training logs and curves

### 4.3 Missing experimental baselines

- RamCOM
- MRA / RMA
- BaseGTA from [17]
- ImpGTA from [17]
- AIM from [17] as a named and documented baseline mechanism

### 4.4 Missing reviewer-required support

- [17] comparison section and executable baseline support
- RL training protocol and timing details
- communication overhead and scalability instrumentation
- parameter sensitivity experiments for `mu_1`, `mu_2`, threshold terms

## 5. Error Logic List

| Code location | Current behavior | Paper reference | Audit result |
| --- | --- | --- | --- |
| `MyMethod/Auction_Framework_Chengdu.py:473-483` | FPSA bid uses clipped heuristic visible-price minus route cost | Eq.1, Algorithm 3 line 10 | `🔧` does not implement `p_min + (alpha * Delta_d + beta * g(c)) * gamma * p'_tau` |
| `MyMethod/Auction_Framework_Chengdu.py:486-500` | FPSA winner chosen without explicit deadline/capacity validity gate | Algorithm 3 lines 8-12 | `🔧` first-layer validity logic is incomplete |
| `MyMethod/Auction_Framework_Chengdu.py:510-523`, `MyMethod/config.py:10` | RVA uses static `COOP_QUALITY` lookup | Eq.3, Algorithm 3 line 20 | `🔧` paper requires dynamic `Qbar_P^Loc / T_Loc` |
| `MyMethod/Auction_Framework_Chengdu.py:525-526` | Second-lowest payment exists, but no upper-limit filter | Eq.4, Algorithm 3 lines 22-24 | `⚠️` payment rule is present but constraint handling is incomplete |
| `MyMethod/Auction_Framework_Chengdu.py:530-538` | Local cross-platform revenue computed as `p_tau - MU_1 * p_tau` | Eq.5 | `🔧` should use realized payment relation, not visible-price ratio |
| `MyMethod/Auction_Framework_Chengdu.py:326-333` | Threshold averaged over matched pairs | Eq.7, Algorithm 2 line 14 | `🔧` should average over all pairs in `M_t` |
| `MyMethod/Auction_Framework_Chengdu.py:593-601` | Global KM or greedy used before threshold split | Algorithm 2 lines 10-15 | `🔧` the paper first builds per-task best tuples `G`, then thresholds them |
| `MyMethod/Auction_Framework_Chengdu.py:558-569`, `827-895` | Batches are precomputed by fixed time buckets | Algorithm 1 lines 3-5 | `🔧` the paper describes online accumulation with explicit `t_cum == Delta_b` |
| `MyMethod/Auction_Framework_Chengdu.py:827-932` | Runner accumulates counts and revenue but returns no matching plan | Algorithm 1 lines 10-12 | `🔧` no explicit `M` is produced or returned |
| `MyMethod/Auction_Framework_Chengdu.py:896-902` | Local revenue added from residual `re_schedule` at batch end | Eq.5 | `⚠️` accounting is schedule-state dependent, not clearly tied to paper-defined revenue events |

## 6. Duplicate Logic List

The repository contains three parallel code families: legacy, refactor, and the newer `MyMethod` draft. The simulation substrate is mostly duplicated instead of shared.

| Logic area | Duplicate locations | Audit note |
| --- | --- | --- |
| Task loading | `Tasks_ChengDu.py:33-87`, `refactor/data.py:18-44` | Same data source, duplicated parsing logic |
| Graph loading and shortest path | `GraphUtils_ChengDu.py`, `refactor/graph.py` | Two route-graph implementations with similar responsibilities |
| Station generation | `Framework_ChengDu.py:86-130`, `refactor/data.py:45-131` | Same station partitioning logic duplicated |
| Initial courier schedule generation | `Framework_ChengDu.py:160-266`, `refactor/framework.py:17-126` | Same recursive scheduling logic duplicated |
| Movement simulation | `Framework_ChengDu.py:270-325`, `MyMethod/Auction_Framework_Chengdu.py:662-760` | Same "advance courier along route" concern implemented twice |
| Matching / bidding helpers | `MethodUtils_ChengDu.py`, `refactor/method_utils.py` | Same old heuristic functions duplicated |
| Greedy / CombinKM baseline runners | `Framework_ChengDu.py:328-451`, `refactor/algorithm.py:15-255` | Same baseline family duplicated |
| Revenue / experiment printing | `Framework_ChengDu.py`, `refactor/framework.py`, `MyMethod/Auction_Framework_Chengdu.py` | Metrics are computed in separate incompatible ways |

Assessment:

- simulation logic should become reusable infrastructure
- assignment logic should be the only part swapped between CAPA, RL-CAPA, and baselines
- current duplication makes paper-faithful repair harder and error-prone

## 7. Fallback / Degradation Logic List

These paths violate `docs/agent.md`'s prohibition on hidden fallback logic.

| Code location | Fallback / degradation behavior | Audit result |
| --- | --- | --- |
| `MyMethod/Auction_Framework_Chengdu.py:266-299` | If KM fails, fall back to greedy sorted matching | `禁止` |
| `MyMethod/Auction_Framework_Chengdu.py:671-673` | If no shortest path is found, fabricate `[current, target]` path | `禁止` |
| `MyMethod/Auction_Framework_Chengdu.py:701-705` | If segment length is invalid, jump directly to next node | `禁止` |
| `MyMethod/Auction_Framework_Chengdu.py:714-716` | If move distance is insufficient, still jump to the next node as a conservative approximation | `禁止` |
| `MyMethod/Auction_Framework_Chengdu.py:118-137` | Remap tasks outside the largest connected component to a sampled nearest node | `禁止` for paper-faithful mainline |
| `MyMethod/Auction_Framework_Chengdu.py:408-420` | If no seeding points exist, synthesize random local stations and couriers | `禁止` |
| `MyMethod/Auction_Framework_Chengdu.py:442-451` | If no seeding points exist, synthesize random partner couriers | `禁止` |

Assessment:

- these paths should not remain in the paper-faithful main branch
- if retained at all, they must live in an explicitly labeled ablation or data-cleaning path

## 8. Repair Plan

Priority is ordered by paper dependency, not by implementation convenience.

### P0. Establish a single authoritative implementation surface

- keep `MyMethod/Auction_Framework_Chengdu.py` only as temporary evidence
- stop extending legacy and `refactor/` copies
- isolate reusable infrastructure: entities, graph access, task loading, simulation advance, metrics

### P1. Repair CAPA heuristic core first

- implement paper-faithful utility and feasibility helpers as standalone functions
- implement explicit CAMA data structures: `S_tau`, `M_t`, `G`, `M_lo`, `L_cr`
- fix Eq.7 threshold to use all pairs in `M_t`
- implement explicit CAPA runner state: `M`, `Gamma_S`, `Gamma_t`, `t_cum`

### P2. Repair DAPA / DLAM

- replace heuristic FPSA bid with Eq.1
- enforce per-courier validity checks before bidding
- implement dynamic `f(P) = Qbar_P^Loc / T_Loc`
- implement payment upper-limit checks and paper-faithful settlement
- repair Eq.5 revenue accounting

### P3. Add paper-faithful tests before any RL work

- unit tests for Eq.6 and Eq.7
- unit tests for Eq.1-Eq.4 bidding and settlement
- scenario tests for Algorithm 2 local-vs-cross split
- end-to-end test for Algorithm 1 batch lifecycle and returned matching plan

### P4. Implement RL-CAPA from scratch on top of repaired CAPA modules

- batch-level environment `M_b`
- parcel-level environment `M_m`
- DDQN models, replay buffer, target networks, epsilon-greedy, optimizer step
- joint training loop with checkpoints and logs

### P5. Rebuild experiments and reviewer support

- evaluation runner for CAPA and RL-CAPA
- baseline implementations: RamCOM, MRA / RMA, BaseGTA, ImpGTA
- parameter sensitivity experiments
- communication overhead and scalability measurements

## 9. Acceptance Checklist

Phase 4-7 should only be considered complete when all of the following are true.

- [ ] A standalone CAPA implementation exists and returns an explicit matching plan `M`
- [ ] Algorithm 1 lines 1-12 are all satisfied without hidden state substitutions
- [ ] Algorithm 2 lines 1-20 are all satisfied with explicit `S_tau`, `M_t`, `G`, `M_lo`, `L_cr`
- [ ] Algorithm 3 lines 1-29 are all satisfied with paper-faithful FPSA, RVA, and payment logic
- [ ] Eq.1-Eq.7 are all implemented exactly or documented with an explicit justified interpretation
- [ ] Eq.5 revenue accounting matches realized local and cross-platform payments
- [ ] No forbidden fallback / degradation path remains in the paper-faithful execution path
- [ ] `M_b` exists with real `S_b`, `A_b`, `P_b`, `R_b`
- [ ] `M_m` exists with real `S_m`, `A_m`, `P_m`, `R_m`
- [ ] RL-CAPA includes online Q-net, target Q-net, replay buffer, epsilon-greedy, target update, optimizer step
- [ ] Joint RL training loop runs end to end and writes real training artifacts
- [ ] Evaluation loop exists for CAPA, RL-CAPA, and all baselines
- [ ] Baselines include RamCOM, MRA / RMA, Greedy, BaseGTA, and ImpGTA
- [ ] Reviewer-required experiments and documentation are reproducible from repository scripts

## Final Audit Conclusion

- current state: partial CAPA draft, no RL-CAPA
- most paper-faithful implemented component: Eq.6 utility
- main correctness gaps: Eq.1, Eq.5, Eq.7, Algorithm 2 set logic, Algorithm 1 runner semantics
- main architectural gap: duplicated simulation code and absence of reusable paper modules
- main compliance gap: several forbidden fallback / degradation paths remain in the current heuristic implementation
