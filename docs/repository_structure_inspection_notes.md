# Repository Structure Inspection Notes

Phase 2 notes for `docs/agent.md`.

Purpose:

- inspect repository structure
- map current source files to paper modules
- identify missing modules, partial implementations, and broken claims
- prepare inputs for Phase 3 audit reporting

## 1. Python Source Structure

Complete `.py` file structure in the current repository:

```text
DistanceUtils.py
Framework_ChengDu.py
MethodUtils_ChengDu.py
GraphUtils_ChengDu.py
Tasks_ChengDu.py
MyMethod/config.py
MyMethod/classDefine.py
MyMethod/km_matcher.py
MyMethod/Auction_Framework_Chengdu.py
refactor/algorithm.py
refactor/data.py
refactor/framework.py
refactor/graph.py
refactor/method_utils.py
refactor/entity.py
```

## 2. File-By-File Mapping

| File | Function / use | Paper module mapping | Notes |
| --- | --- | --- | --- |
| `DistanceUtils.py` | Haversine distance helper for lat/lng node distance computation. | `非论文模块` | Generic geometry utility only. |
| `GraphUtils_ChengDu.py` | Loads OSM-like road graph, builds graph context, shortest-path search, nearest-node lookup. | `数据加载 / 路网基础设施` | Supports all route-based feasibility checks, but is not paper-specific logic. |
| `Tasks_ChengDu.py` | Defines `Task`, loads raw task files from `Data/`, includes `Combin()` packaging helper. | `数据加载 + 旧基线辅助` | Not a CAPA/CAMA/DAPA implementation. `Combin()` appears to be legacy batching/packing logic. |
| `Framework_ChengDu.py` | Legacy experiment entry point: builds stations/couriers, generates initial schedules, runs `Greedy()`. | `实验 / 旧基线 runner` | Does not implement CAPA, DAPA, or RL-CAPA. |
| `MethodUtils_ChengDu.py` | Legacy matching/bidding helpers: `FBP_*`, `BM_*`, `Combin`, `WalkAlongRoute`. | `旧基线辅助` | Uses heuristic bidding and KM/greedy utilities, but not the paper equations or pseudocode. |
| `MyMethod/config.py` | Current heuristic experiment configuration: utility, threshold, batch size, payment coefficients, platform counts. | `CAPA/DAPA 配置` | Closest current config for paper-style heuristic pipeline, but values and semantics are not fully paper-faithful. |
| `MyMethod/classDefine.py` | Current entity layer: `Station`, `Courier`, `LocalPlatform`, `PartnerPlatform`, wrappers, registry. | `CAPA/DAPA 实体定义` | Supports current multi-platform heuristic implementation. |
| `MyMethod/km_matcher.py` | Hungarian/KM maximum-weight matcher implementation. | `CAMA 本地匹配辅助` | A reusable solver, not paper logic by itself. |
| `MyMethod/Auction_Framework_Chengdu.py` | Main current heuristic pipeline: candidate generation, utility, threshold split, FPSA, RVA, batching, metrics, plotting. | `CAPA runner + CAMA partial + DAPA partial + 实验 runner` | This is the only file that meaningfully attempts to implement the paper's heuristic method. It does not implement RL-CAPA. |
| `refactor/entity.py` | Refactored entities for legacy pipeline. | `旧基线辅助` | Structural cleanup of old code, not paper module completion. |
| `refactor/data.py` | Refactored task/station loading plus a small unit test. | `数据加载` | Still tied to legacy experiment structure. |
| `refactor/framework.py` | Refactored legacy experiment driver building schedules and running `Greedy` / `CombinKM`. | `实验 / 旧基线 runner` | Not CAPA or RL-CAPA. |
| `refactor/graph.py` | Refactored graph import, shortest-path, nearest-node utilities plus a test. | `数据加载 / 路网基础设施` | Duplicate of `GraphUtils_ChengDu.py` in cleaner form. |
| `refactor/method_utils.py` | Refactored legacy matching/bidding helpers and KM matcher copy. | `旧基线辅助` | Heuristic helper layer for old experiments. |
| `refactor/algorithm.py` | Refactored `Greedy` and `CombinKM`. | `旧基线 / 实验` | Not CAPA/DAPA/RL-CAPA. |

## 3. Source Tree Assessment

The codebase currently falls into three groups:

1. Legacy Chengdu pipeline:
   - `Framework_ChengDu.py`
   - `MethodUtils_ChengDu.py`
   - `Tasks_ChengDu.py`
   - `GraphUtils_ChengDu.py`

2. Refactor copy of the same legacy pipeline:
   - `refactor/*.py`

3. Newer paper-oriented heuristic attempt:
   - `MyMethod/Auction_Framework_Chengdu.py`
   - `MyMethod/config.py`
   - `MyMethod/classDefine.py`
   - `MyMethod/km_matcher.py`

Only group 3 has meaningful overlap with CAPA/CAMA/DAPA from the paper.

## 4. RL-Related Code Inspection

Repo-wide source inspection result across all `.py` files:

- DDQN / DQN network definition: `未发现`
- Replay buffer: `未发现`
- Target network: `未发现`
- Soft update / hard update: `未发现`
- Training loop:
  - episode loop: `未发现`
  - environment step loop: `未发现`
  - optimization step / backprop: `未发现`
- Epsilon-greedy exploration: `未发现`
- Torch / TensorFlow / Keras dependency usage: `未发现`
- RMSprop optimizer usage in source code: `未发现`

Observation:

- The only RL-related material in the repository is in `docs/agent.md`, the paper markdown, and review comments.
- There is no real RL-CAPA implementation in current source files.
- Therefore any repository-level claim that RL-CAPA currently exists in executable form would be false.

## 5. CAPA-Related Code Inspection

### 5.1 Where CAPA-like logic exists

The only CAPA-like implementation attempt is in:

- `MyMethod/Auction_Framework_Chengdu.py`

Key subareas in that file:

- utility computation: `compute_utility()` at line 196
- threshold computation: `compute_threshold()` at line 326
- local split: `split_local_or_cross()` at line 336
- courier FPSA bid: `_courier_bid_fpsa()` at line 473
- platform RVA bid: `platform_bid_rva()` at line 510
- cross-platform settlement: `settle_cross_platform()` at line 530
- local phase runner: `_local_phase_step()` at line 574
- cross-platform phase runner: `_cross_phase_step()` at line 620
- end-to-end multi-platform pipeline: `run_multiplatform_time_stepped()` at line 827

### 5.2 Utility `u(τ,c)` and Eq.6

Status: `存在，基本匹配 Eq.6`

Evidence:

- `compute_delta_weight()` computes capacity ratio style term.
- `compute_best_insert_and_detour()` computes insertion-based detour ratio.
- `compute_utility()` combines them as:
  - `u = gamma * delta_w + (1.0 - gamma) * delta_d`

Assessment:

- This is the closest paper-faithful formula in the repo.
- It matches the Eq.6 structure.

### 5.3 Dynamic threshold `T_h` and Eq.7

Status: `存在，但部分不匹配 Eq.7`

Evidence:

- `compute_threshold()` returns `omega * (sum(vs) / len(vs))`.

Mismatch:

- Paper Eq.7 uses average utility over all potential matching pairs in `M_t`.
- Current implementation computes the average over `matched_pairs`, not over the full candidate universe `M_t`.
- This changes the threshold semantics and therefore changes CAMA behavior.

### 5.4 FPSA bid function and Eq.1

Status: `存在，但不匹配 Eq.1`

Evidence:

- `_courier_bid_fpsa()` defines:
  - `p_visible = MU_1 * task.fare`
  - route-based cost penalty
  - service-score multiplier
  - clipped bid bounded by `p_visible`

Mismatch with Eq.1:

- no `p_min`
- no paper-defined `α_{c_P^i}`
- no paper-defined `β_{c_P^i}`
- no direct `γ * p'_τ` multiplicative structure
- no paper-defined `g(c_P^i)` aggregation beyond a simple `service_score`

Conclusion:

- It is a heuristic FPSA-like bid, not the paper's Eq.1.

### 5.5 RVA bid function and Eq.3

Status: `存在，结构部分匹配 Eq.3`

Evidence:

- `platform_bid_rva()` distinguishes:
  - `len(bucket) >= 2`
  - otherwise single-bidder case
- It computes:
  - `BR = p_prime + MU_2 * fare * quality_factor`
  - quality factor only used when multiple platforms bid
  - single platform falls back to multiplier `1.0`

What matches:

- Two-case logic for `|P_τ| = 1` and `|P_τ| >= 2`
- Base form `p_prime + μ_2 * p_τ` / `p_prime + f(P) μ_2 p_τ`

What does not match:

- `f(P)` is pulled from static config `COOP_QUALITY`, not computed as `Q̄_P^Loc / T_Loc`
- no explicit upper payment limit filtering before selecting the winner

Conclusion:

- Eq.3 is only partially implemented.

### 5.6 Second-lowest payment rule and Eq.4

Status: `存在`

Evidence:

- `pay_price = bids[1][1] if len(bids) >= 2 else bids[0][1]`

Assessment:

- For the multi-platform case, this is the paper's second-lowest-payment behavior.
- This is one of the few DAPA elements that is correctly reflected at a high level.

### 5.7 Single-platform special case and Algorithm 3 Lines 26-28

Status: `存在`

Evidence:

- In `platform_bid_rva()`, if only one platform bids:
  - `multi` is false
  - `BR = p_prime + MU_2 * fare`
  - `pay_price = bids[0][1]`

Assessment:

- This reproduces the intended single-bidder payment path at a high level.
- It is embedded in `platform_bid_rva()` rather than represented as explicit Algorithm 3 lines.

### 5.8 CAPA control-flow coverage

Status: `部分存在`

What exists in `MyMethod/Auction_Framework_Chengdu.py`:

- fixed-time batching via `make_batches_by_time()`
- in-batch local phase `_local_phase_step()`
- cross-platform phase `_cross_phase_step()`
- local/cross revenue tracking

What is missing or diverges from the paper:

- no explicit `CAPA` function with Algorithm 1's state variables `M`, `Γ_S`, `t_cum`
- no exact `CAMA` function matching Algorithm 2 line-by-line
- no exact `DAPA` function matching Algorithm 3 line-by-line
- local stage uses global greedy/KM assignment, not per-task best-pair candidate set construction from Algorithm 2
- batch trigger logic is pre-bucketed by time rather than online `t_cum == Δb`
- no explicit returned matching plan set `M`

## 6. Legacy / Non-Paper Logic Found

The following logic appears repeatedly in the legacy and refactor trees:

- `Greedy`
- `CombinKM`
- `FBP_GA`
- `FBP_GA1`
- `FBP_KM`
- `FBP_cKMB`
- `BM_cKMB`
- `BM_KM`
- `Combin`

Assessment:

- These are not CAPA/CAMA/DAPA from the paper.
- They are older heuristic or experimental matching methods.
- They use ad hoc bidding and insertion rules.
- They should be treated as baselines, prototypes, or legacy code, not as faithful paper implementations.

## 7. Missing Modules Relative to the Paper

### Completely missing

- RL environment for `M_b`
- RL environment / agent interface for `M_m`
- DDQN model definitions
- replay buffer
- target networks
- epsilon-greedy exploration logic
- optimizer step / training loop
- checkpointing
- RL evaluation pipeline
- RL logging / reward/loss output
- [17] baselines:
  - `AIM`
  - `BaseGTA`
  - `ImpGTA`
- RamCOM baseline
- MRA / RMA baseline

### Present but incomplete / incorrect

- CAPA runner: partial
- CAMA: partial
- DAPA: partial
- Eq.1: incorrect
- Eq.3: partial
- Eq.4: present
- Eq.5 revenue handling: incorrect
- Eq.6 utility: present
- Eq.7 threshold: partial

## 8. High-Level Interpretation for Phase 3

The repository currently does not contain a full paper-faithful implementation.

Most important conclusions:

1. The repo contains many legacy heuristic files unrelated to CAPA/RL-CAPA.
2. The only serious attempt at the paper's heuristic method is `MyMethod/Auction_Framework_Chengdu.py`.
3. Even that file is only a partial heuristic approximation:
   - utility is close
   - threshold is partial
   - FPSA bid is not paper-faithful
   - RVA bid is partial
   - revenue accounting is wrong for paper Eq.5
4. There is no executable RL-CAPA implementation at all.
5. Phase 3 audit report should treat the current repo as:
   - legacy baseline code
   - one partial CAPA prototype
   - zero real RL code

## 9. Recommended Inputs to Phase 3 Audit Report

Phase 3 should explicitly cover:

- which files are legacy / refactor duplicates versus active implementation candidates
- why `MyMethod/Auction_Framework_Chengdu.py` is only partial CAPA
- why current repo cannot claim RL-CAPA
- exact gaps between the paper's Algorithm 1/2/3 and the current control flow
- exact formula mismatches for Eq.1, Eq.5, Eq.7
- baseline implementation gaps for reviewer-required comparison with [17]
