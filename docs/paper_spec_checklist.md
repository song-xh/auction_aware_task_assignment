# Paper Spec Checklist

Phase 1 extraction from:

1. `docs/Auction-Aware Crowdsourced Parcel Assignment for Cooperative Urban Logistics.md`
2. `docs/MinerU_markdown_Competition_and_Cooperation_Global_Task_Assignment_in_Spatial_Crowdsourcing_2039180845507551232.md`
3. `docs/review.md`

Legend:

- `✅` 已实现
- `❌` 缺失
- `⚠️` 部分实现
- `🔧` 已实现但与论文不一致/明显错误

Current repo evidence mainly comes from:

- `MyMethod/Auction_Framework_Chengdu.py`
- `MyMethod/config.py`
- `Framework_ChengDu.py`
- `refactor/algorithm.py`
- `refactor/framework.py`

## 1. Formula Checklist

| Item | Paper spec | Status | Repo note |
| --- | --- | --- | --- |
| Eq.1 | `B_F(c_P^i, τ) = p_min + (α_{c_P^i}·Δd_τ + β_{c_P^i}·g(c_P^i))·γ·p'_τ` | `🔧` | `_courier_bid_fpsa()` (`MyMethod/Auction_Framework_Chengdu.py:473-483`) uses `THETA_BID * MU_1 * fare * (0.5 + 0.5*g_score) - cost`; no `p_min`, no `α/β`, no paper form. |
| Eq.2 | `p'(τ, c_win^P) = max{ B_F(c_P^i, τ) }` | `⚠️` | `internal_fpsa_for_platform()` (`MyMethod/Auction_Framework_Chengdu.py:486-507`) does select max bid, but it is built on incorrect Eq.1 and lacks paper-faithful validity handling. |
| Eq.3 | `B_R(P, τ) = p'(τ,c_win^P)+μ_2 p_τ` if `|P_τ|=1`; else `p'(τ,c_win^P)+f(P)μ_2 p_τ` | `⚠️` | `platform_bid_rva()` (`MyMethod/Auction_Framework_Chengdu.py:510-527`) follows the two-case structure, but `f(P)` is a fixed config lookup (`MyMethod/config.py:7-10`), not paper-defined historical cooperation quality `Q̄_P^Loc / T_Loc`. |
| Eq.4 | `p'(τ, P_win) = min{ B_R(P,τ) | P ∈ (P \ P_win) }` | `⚠️` | `platform_bid_rva()` pays the second-lowest bid when there are at least two bidders, but no paper-stated upper-payment-limit screening is enforced before winner/payment selection. |
| Eq.5 | `Rev_S(Γ_L, C_L, P)` = local-platform total revenue from inner and cross assignments | `🔧` | Definition 4 and Section 3.4 imply inner term `p_τ - Rc(τ,c)` plus cross term `p_τ - p'(τ,c)`. The markdown rendering of Eq.5 is truncated, so this interpretation is inferred from the surrounding text. Current `settle_cross_platform()` (`MyMethod/Auction_Framework_Chengdu.py:530-538`) uses `p_τ - MU_1·p_τ`, not `p_τ - pay_price`; local revenue aggregation is not paper-faithful. |
| Eq.6 | `u(τ,c) = γ·Δw_τ + (1-γ)·Δd_τ` | `✅` | `compute_utility()` (`MyMethod/Auction_Framework_Chengdu.py:196-202`) matches the paper form. |
| Eq.6a | `Δw_τ = 1 - (Σ_{ψ∈Ψ_c} w_ψ + Σ_{τ∈Γ_c} w_τ) / w_c` | `✅` | `compute_delta_weight()` (`MyMethod/Auction_Framework_Chengdu.py:190-193`) uses current carried weight plus task weight over max capacity. |
| Eq.6b | `Δd_τ = min_i π(l_i,l_{i+1}) / (π(l_i,l_τ)+π(l_τ,l_{i+1}))` | `✅` | `compute_best_insert_and_detour()` (`MyMethod/Auction_Framework_Chengdu.py:138-187`) searches insertion positions and uses `base / (a+b)`. |
| Eq.7 | `T_h = ω · Σ_{(τ_i,c_j)∈M_t} u(τ_i,c_j) / |M_t|` | `⚠️` | `compute_threshold()` (`MyMethod/Auction_Framework_Chengdu.py:326-333`) computes `ω * avg(u)`, but over final matched pairs, not over all potential pairs `M_t` defined in Algorithm 2. |
| M_b reward | `R_b(s_t,a_t)` is batch revenue `Rev_S(Γ_Loc, C_Loc, P)`; cumulative objective `Σ γ^t Rev_S^t(...)` | `❌` | No RL environment, no DDQN, no batch-size reward implementation found outside docs. |
| M_m reward | `R_m(s_m,a_m) = p_τ - Rc(τ,c)` if local and successful; `p_τ - p'_τ(τ,c)` if cross and successful; else `0` | `❌` | No parcel-level RL reward implementation found outside docs. |

## 2. Algorithm Checklist

### Algorithm 1: CAPA

| Line | Paper step | Status | Repo note |
| --- | --- | --- | --- |
| 1 | Initialize `M ← ∅`, `Γ_S ← ∅`, `t_cum = 0` | `⚠️` | `main()` and `run_multiplatform_time_stepped()` initialize counters/pools, but no explicit global `M` or `t_cum` state (`MyMethod/Auction_Framework_Chengdu.py:827-845`, `994-1021`). |
| 2 | `while timeline t is not terminal` | `⚠️` | Implemented as loop over prebuilt batches and in-batch time steps, not the paper's online stream loop. |
| 3 | Retrieve new arriving parcels `Γ_t` | `⚠️` | `arrived = [t for t in unassigned if s_time <= t0]` in `run_multiplatform_time_stepped()` (`856-859`). |
| 4 | `Γ_S ← Γ_S ∪ Γ_t` | `⚠️` | Implicit through `unassigned`/batch lists, not explicit paper state. |
| 5 | `if t_cum == Δb` trigger batch | `⚠️` | Batches are precomputed by `make_batches_by_time()` (`558-569`) using fixed `BATCH_SECONDS`; no explicit `t_cum` counter. |
| 6 | Retrieve available inner couriers `C_S` | `✅` | `couriers_local = [ic.ref for ic in local_platform.couriers]` (`829-831`). |
| 7 | Retrieve available platforms `P_S` | `✅` | `partners` passed into `run_multiplatform_time_stepped()` and iterated in cross phase. |
| 8 | Call CAMA on `(Γ_S, C_S)` | `⚠️` | `_local_phase_step()` is the nearest implementation (`574-615`), but it does not follow Algorithm 2 line-for-line. |
| 9 | Call DAPA on `(P_S, L_cr)` | `⚠️` | `_cross_phase_step()` (`620-657`) exists, but diverges from paper DAPA details. |
| 10 | `M ← M ∪ M_lo ∪ M_cr` | `⚠️` | Assignment counts and revenue are accumulated, but no explicit returned matching plan `M`. |
| 11 | Reset `M_cr`, `M_lo`, `Γ_t`, `t_cum` | `⚠️` | Local variables reset by function scope / next loop, but no paper-style state reset block. |
| 12 | Return `M` | `❌` | Multi-platform runner prints metrics and updates `sink`; it does not return a matching set. |

### Algorithm 2: CAMA

| Line | Paper step | Status | Repo note |
| --- | --- | --- | --- |
| 1 | Initialize `M_lo`, `L_cr`, `M_t`, `G` | `⚠️` | `_local_phase_step()` initializes local containers, but not the exact paper sets (`574-578`). |
| 2 | For each parcel `τ_i ∈ Γ_t` | `✅` | `enumerate_candidates()` iterates tasks (`223-236`). |
| 3 | `S_τ ← ∅` | `❌` | No explicit per-task candidate set object. |
| 4 | For each courier `c_j ∈ C_S` | `✅` | `enumerate_candidates()` loops candidate couriers (`224-225`). |
| 5 | Check deadline and capacity feasibility | `✅` | Local candidate enumeration checks weight and deadline (`226-235`). |
| 6 | Compute utility `u(τ_i,c_j)` | `✅` | `compute_utility()` called at `231`. |
| 7 | Insert tuple into `S_τ` | `⚠️` | Tuples go into global `cands`, not explicit per-task `S_τ`. |
| 8 | If `|S_τ| != 0` | `⚠️` | Handled implicitly by whether task produced any candidate tuples. |
| 9 | `M_t ← M_t ∪ S_τ` | `⚠️` | The repo tracks candidates, but not a named `M_t` with paper semantics. |
| 10 | Pick `arg max u(τ_i,c_j)` in `S_τ` | `❌` | Current logic uses global greedy/KM matching over all pairs, not per-task best-pair extraction. |
| 11 | `G ← G ∪ {(τ_i,c_j,u)}` | `❌` | No explicit candidate-best set `G`. |
| 12 | Else branch for no feasible courier | `⚠️` | Implicit when a task yields no candidate pair. |
| 13 | `L_cr ← L_cr ∪ {τ_i}` | `⚠️` | Tasks left in `remaining_tasks` later become cross candidates, but no direct line-level append at this stage. |
| 14 | Compute threshold `T_h` via Eq.7 on `M_t` | `🔧` | `compute_threshold()` exists, but uses matched pairs instead of `M_t` (`326-333`). |
| 15 | For each tuple in `G` | `⚠️` | `split_local_or_cross()` iterates final `matched_pairs`, not the paper's `G` (`336-345`). |
| 16 | If `u(τ_i,c_j) ≥ T_h` | `✅` | Threshold comparison exists in `split_local_or_cross()` (`339-344`). |
| 17 | `M_lo ← M_lo ∪ {(τ_i,c_j)}` | `✅` | `apply_local_assignment()` lands local matches (`348-360`). |
| 18 | Else | `✅` | Implemented through threshold split. |
| 19 | `L_cr ← L_cr ∪ {τ_i}` | `✅` | Low-utility tasks remain for cross phase as `remaining_after_local` / `cross_candidates`. |
| 20 | Return `M_lo, L_cr` | `⚠️` | `_local_phase_step()` returns landed local pairs and remaining tasks, not exact paper sets. |

### Algorithm 3: DAPA

| Line | Paper step | Status | Repo note |
| --- | --- | --- | --- |
| 1 | Initialize `M_cr ← ∅` | `⚠️` | `_cross_phase_step()` initializes counters/lists, but not a named `M_cr` set (`620-631`). |
| 2 | For each cross parcel `τ_i ∈ L_cr` | `✅` | Loop over `remaining_tasks` in `_cross_phase_step()` (`633-650`). |
| 3 | Step 1 comment: FPSA process | `✅` | FPSA logic exists via `internal_fpsa_for_platform()`. |
| 4 | `B_{τ_i} ← ∅` | `⚠️` | Built implicitly in `platform_bid_rva()` as `bucket`, not explicit in outer loop. |
| 5 | For each platform `P_j ∈ P_S` | `✅` | `_cross_phase_step()` iterates platforms (`623-626`). |
| 6 | `B_F ← ∅` | `⚠️` | `internal_fpsa_for_platform()` only tracks best bid, not an explicit `B_F` set. |
| 7 | Obtain `C_{P_j}` | `✅` | Uses `platform.couriers` (`494-495`). |
| 8 | For each courier `c_{P_j}^k ∈ C_{P_j}` | `✅` | Loop inside `internal_fpsa_for_platform()` (`494-498`). |
| 9 | If `(c_{P_j}^k, τ_i)` is valid | `⚠️` | No explicit paper-style capacity/deadline validity gate in FPSA; bid function itself only checks route reachability. |
| 10 | Compute `B_F(c_{P_j}^k, τ_i)` via Eq.1 | `🔧` | `_courier_bid_fpsa()` exists, but formula is not Eq.1 (`473-483`). |
| 11 | Insert tuple into `B_F` | `⚠️` | No explicit `B_F` set; only running best bid retained. |
| 12 | If `B_F` non-empty | `✅` | `if best is not None and best_price > 0` (`499-500`). |
| 13 | Sort `B_F` descending | `⚠️` | Implemented by tracking max rather than sorting the full set. |
| 14 | Pick first tuple as internal winner | `⚠️` | The winner is picked, but only via running max, not explicit tuple extraction from sorted `B_F`. |
| 15 | Insert winner tuple into `B_{τ_i}` | `⚠️` | Winner records stored in `out[t.num]`; parcel-level bid set is reconstructed later. |
| 16 | Step 2 comment: RVA process | `✅` | RVA logic exists via `platform_bid_rva()`. |
| 17 | If `|B_{τ_i}| ≥ 2` | `✅` | `multi = len(bucket) >= 2` (`518`). |
| 18 | `B_R ← ∅` | `✅` | `bids = []` (`517`). |
| 19 | For each tuple in `B_{τ_i}` | `✅` | `for pid, p_prime in bucket` (`519-523`). |
| 20 | Compute `B_R(P_j, τ_i)` | `⚠️` | Formula structure exists, but `f(P)` source and upper-limit logic are not paper-faithful. |
| 21 | Insert tuple into `B_R` | `✅` | `bids.append((pid, BR))` (`523`). |
| 22 | Sort `B_R` ascending | `✅` | `bids.sort(...)` (`524`). |
| 23 | Pick first tuple as winner | `✅` | `winner_pid = bids[0][0]` (`525`). |
| 24 | Set payment to second-lowest bid | `✅` | `pay_price = bids[1][1] if len(bids) >= 2 else bids[0][1]` (`526`). |
| 25 | `M_cr ← M_cr ∪ {(τ_i, c_{P_win})}` | `✅` | Winner courier inserted and task appended to `assigned_tasks` (`636-650`). |
| 26 | If `|B_{τ_i}| == 1` | `✅` | Single-bidder case is handled by `len(bucket) < 2`. |
| 27 | `p'(τ_i, P_win) = B_F(...) + μ_2 p_τ` | `✅` | In the single-bidder case, `BR = p_prime + MU_2 * fare` (`520-522`) and `pay_price = bids[0][1]` (`526`). |
| 28 | `M_cr ← M_cr ∪ {(τ_i, c_{P_win}^k)}` | `✅` | Same insertion path as line 25. |
| 29 | Return `M_cr` | `⚠️` | `_cross_phase_step()` returns counts, prices, and `assigned_tasks`, not an explicit matching set. |

## 3. MDP Checklist

### M_b = (S_b, A_b, P_b, R_b)

| Component | Paper definition | Status | Repo note |
| --- | --- | --- | --- |
| `A_b` | Discrete batch-size choices `[h_L, h_{L+1}, ..., h_M]` | `❌` | Repo has only fixed `BATCH_SECONDS = 10 * 60` (`MyMethod/config.py:13`). |
| `S_b` | `(|Γ_t^Loc|, |C_t^Loc|, |D|, |T|)` | `❌` | No batch-size RL state builder exists. |
| `P_b` | Transition `P_b(s_{t+1} \| s_t, a_t)` | `❌` | No RL environment exists. |
| `R_b` | Immediate reward is batch revenue `Rev_S(Γ_Loc, C_Loc, P)` | `❌` | No batch-size RL reward implementation exists. |
| `M_b` reward objective | `E = Σ_{t=0}^∞ γ^t Rev_S^t(Γ_Loc, C_Loc, P)` | `❌` | No DDQN training loop, replay buffer, target network, or optimizer code found outside docs. |

### M_m = (S_m, A_m, P_m, R_m)

| Component | Paper definition | Status | Repo note |
| --- | --- | --- | --- |
| `A_m` | Binary action: `1 = cross`, `0 = defer to next batch` | `❌` | Repo uses heuristic threshold routing; no RL action selection exists. |
| `S_m` | `(|ΔΓ|, t_τ, t_cur, Δb)` | `❌` | No parcel-level RL state builder exists. |
| `P_m` | Transition `P_m(s'_m \| s_m, a_m)` | `❌` | No RL environment exists. |
| `R_m` | Piecewise local/cross/zero reward function | `❌` | No parcel-agent reward implementation exists. |
| Reappearance rule | Unassigned parcel reappears next batch as a new agent | `❌` | There is backlog-like task carryover in heuristic code, but no RL agent lifecycle implementation. |

## 4. Experimental Parameters and Configurations

### Table 2

| Parameter | Paper values | Repo note |
| --- | --- | --- |
| `|C|` (NYTaxi) | `0.1K, 0.2K, 0.3K, 0.4K, 0.5K` | No NYTaxi experiment sweep implemented in current repo. |
| `|Γ|` (NYTaxi) | `0.5K, 2K, 5K, 10K, 20K` | Not implemented as a current experiment suite. |
| `|C|` (Synthetic) | `1K, 2K, 3K, 4K, 5K` | Current config fixes local partner scales; no paper sweep. |
| `|Γ|` (Synthetic) | `5K, 20K, 50K, 100K, 200K` | No paper sweep found. |
| Courier capacity `w` | `25, 50, 75, 100, 125` | Current `Courier` uses fixed `50.0`; no sweep (`MyMethod/classDefine.py`). |
| Service radius `rad` (km) | `0.5, 1, 1.5, 2, 2.5` | No paper-faithful radius sweep found. |
| Number of cooperating platforms `|P|` | `2, 4, 8, 12, 16` | Current config fixes `NUM_PARTNER_PLATFORMS = 2` (`MyMethod/config.py:19`). |

### Additional Section 4.1 settings

- Datasets: NYTaxi and Shanghai synthetic dataset.
- Road networks:
  - Shanghai: `216,225` edges, `14,853` nodes.
  - New York: `8,635,965` edges, `157,628` nodes.
- Parcel weights: uniform over `(0, 10)`.
- Courier preference coefficients `α_{c_P^i}` and `β_{c_P^i}`: uniformly generated.
- Parcel deadlines `t_τ`, `t_φ`: `0.5` to `24` hours.
- DQN optimizer: RMSprop.
- Learning rate: `0.001`.
- Discount factor: `0.9`.
- Hardware: Intel i7-9700K@3.6GHz CPU, 16GB RAM.
- Metrics:
  - Total Revenue (TR)
  - Completion Rate (CR)
  - Batch Processing Time (BPT)

### Experimental baselines from the CAPA paper

| Baseline | Source role | Status | Repo note |
| --- | --- | --- | --- |
| RamCOM | Main paper baseline | `❌` | No implementation found. |
| MRA / RMA | Main paper baseline; paper text is inconsistent (`RMA` in setup, `MRA` later) | `❌` | No implementation found. |
| Greedy | Main paper baseline | `⚠️` | `Greedy()` exists in `Framework_ChengDu.py` and `refactor/algorithm.py`, but not audited as paper-faithful baseline yet. |
| CAPA | Main paper heuristic method | `⚠️` | Partial heuristic implementation exists in `MyMethod/Auction_Framework_Chengdu.py`, but not paper-faithful end-to-end. |
| RL-CAPA | Main paper RL method | `❌` | No real RL implementation found. |

## 5. Reference [17] Baselines to Carry Forward

| Method | Extracted definition | Status in current repo |
| --- | --- | --- |
| AIM | Auction-based incentive mechanism: outer platforms bid; inner platform picks minimum bid winner and pays second minimum critical payment; designed for truthfulness, individual rationality, profitability, efficiency. | `❌` as a named faithful baseline. Current code has a different two-layer auction, not [17] AIM. |
| BaseGTA | Greedy cross-platform task assignment: inner worker first; if none, outer platforms with idle workers bid via AIM. | `❌` |
| ImpGTA | Prediction-based GTA: uses temporal window `Δτ` and predicted task distribution `T̃` to decide inner/outer conditions based on worker sufficiency or expected reward threshold. | `❌` |

Key [17] conditions to preserve later:

- BaseGTA inner/outer condition: at least one idle worker.
- ImpGTA inner conditions:
  - `|W^{p_k}| > |T̃_{Δτ}^{p_k}|`
  - or `v_{t_j} ≥ U_exp(T̃_{Δτ}^{p_k})`
- ImpGTA outer conditions:
  - `|W^{p_i}| > |T̃_{Δτ}^{p_i}|`
  - or `su_{ij} ≥ U_exp(T̃_{Δτ}^{p_i})`

## 6. Reviewer Mapping To-Do

### Reviewer 1

- [ ] `R1-W1`: Add a dedicated limitation/validation section covering noisy data, delayed data, strategic behavior, contracts/regulation, and human-in-the-loop or real-world deployment gaps.
- [ ] `R1-W2`: Add explicit communication-overhead, latency, synchronization-cost, and scalability analysis for many platforms/couriers under near-real-time auctions and RL updates.
- [ ] `R1-W3`: Clarify what real-time data must actually be shared across competing platforms, what can remain private, and why the cooperation assumption is operationally plausible.
- [ ] `R1-W4`: Rework the truthfulness claim so it matches the actual mechanism; distinguish system-computed bids from private-valuation auctions and tighten the theory accordingly.
- [ ] `R1-W5`: Add sensitivity analysis for manually chosen parameters such as `μ_1`, `μ_2`, threshold/sensitivity terms, and cost ratios; consider adaptive tuning if justified.

### Reviewer 2

- [ ] `R2-1`: Add a clear, separate comparison section explaining the difference between this paper and [17] in problem setting, mechanism design, and framework structure.
- [ ] `R2-2`: Implement and report [17] baselines `BaseGTA` and `ImpGTA` in the experimental study; include `AIM` discussion where needed.
- [ ] `R2-3`: Document RL training details: training data, protocol, training time, and how the RL model is actually trained and evaluated.

### Reviewer 3

- [ ] `R3-1`: Clarify the role of drop-off parcels versus pick-up parcels in the CPUL scope and explain how drop-off parcels still affect constraints/schedules.
- [ ] `R3-2`: Add a balanced discussion of the limitations of batched assignment compared with instant real-time matching.
- [ ] `R3-3`: Improve Fig. 5 / RL-CAPA explanation so the interaction between `M_b` and `M_m` is explicit.
- [ ] `R3-4`: Strengthen the literature review with a sharper comparative discussion of prior task-assignment and auction methods and how their limits motivate CAPA/RL-CAPA.

## 7. Immediate Audit Conclusions

- The current repo has a partial heuristic implementation around CAMA-like local matching and DAPA-like cross-platform auction in `MyMethod/Auction_Framework_Chengdu.py`.
- Eq.6 is the closest paper-faithful component.
- Eq.1 and Eq.5 are currently inconsistent with the paper.
- Eq.7 and several CAMA/DAPA control-flow details are only partially reflected.
- No real RL-CAPA implementation is present:
  - no `DDQN`
  - no replay buffer
  - no target network
  - no RL environment
  - no batch-size policy learner
  - no cross-or-not policy learner
- Paper baselines from [17] (`BaseGTA`, `ImpGTA`) are absent.
