# agent.md

## Role

You are the primary implementation and verification agent for the paper **"Auction-Aware Crowdsourced Parcel Assignment for Cooperative Urban Logistics"**. Your job is to make the codebase **faithfully match the paper**, not to preserve the current implementation if it deviates from the manuscript. Treat the **paper as the source of truth** for algorithmic behavior and treat the current repository only as a potentially incomplete draft.

The paper defines two main methods:

1. **CAPA**: a heuristic online assignment framework composed of:
   - **CAMA** for local-platform parcel assignment
   - **DAPA / DLAM** for cross-platform parcel assignment via a dual-layer auction

2. **RL-CAPA**: a reinforcement-learning extension that keeps the cross-platform assignment mechanism of DAPA, while learning:
   - **batch-size / time-window selection** via DDQN
   - **cross-or-not decisions** for unassigned parcels via DDQN

Your task is to audit, repair, implement, validate, visualize, and extend the repository accordingly.

---

## Superpowers: Paper-Reading Workflow

Before writing any code, you MUST read and internalize the paper and review documents stored in the project. These serve as the authoritative specification.

### Step 0 — Read the paper and reviews first

Read the following files in order before any implementation:

1. `docs/Auction-Aware_Crowdsourced_Parcel_Assignment_for_Cooperative_Urban_Logistics.md` — the full paper
2. `docs/MinerU_markdown_Competition_and_Cooperation_Global_Task_Assignment_in_Spatial_Crowdsourcing_2039180845507551232.md` — reference [17], which Reviewer 2 requires comparison with
3. `docs/review.md` — the three reviewers' comments

For each file, read it section by section. Extract and note:
- All equations (Eq. 1–7 and the reward functions for M_b, M_m)
- All algorithm pseudocode (Algorithm 1: CAPA, Algorithm 2: CAMA, Algorithm 3: DAPA)
- All MDP definitions (S_b, A_b, R_b, P_b, S_m, A_m, R_m, P_m)
- All parameter settings (Table 2)
- All experimental configurations and baseline methods
- Reviewer concerns W1–W5 (Reviewer 1), points 1–3 (Reviewer 2), points 1–4 (Reviewer 3)
- Reference [17]'s methods (AIM, BaseGTA, ImpGTA) for baseline comparison

### Step 0.1 — Build a specification checklist

After reading, create `docs/paper_spec_checklist.md` containing:
- A checklist of every equation, algorithm, MDP component, and experimental configuration from the paper
- Each item marked as: ✅ implemented / ❌ missing / ⚠️ partial / 🔧 incorrect
- This checklist will guide all subsequent implementation

---

## Non-negotiable implementation rules

### 1) Paper-faithful implementation
- If the repository conflicts with the paper, **the paper wins**.
- Do not silently reinterpret missing logic.
- Do not replace paper-defined mechanisms with easier approximations unless explicitly marked as a new experimental ablation.

### 2) Strict prohibition on fallback logic
The following are **forbidden** unless explicitly approved in a separate experimental branch:
- degradation paths
- fallback logic
- backup heuristics inserted to mask failures
- emergency patches
- local stabilization tricks that alter the intended algorithm
- hidden post-processing
- "if failed then greedy"
- "if missing then random but continue"
- "best effort" surrogate logic that changes the intended decision rule

If the implementation is blocked by an ambiguity, do **not** hide it with a workaround. Instead:
- locate the ambiguity precisely
- document it
- resolve it by the paper text, equations, pseudocode, or reviewer concerns
- if still unresolved, surface it clearly in the audit report and stop at that boundary

### 3) Clean code architecture
- Common logic (e.g., CAPA components, utility functions, constraint checks) must be decomposed into independent modules/functions.
- Every function must have a docstring describing:
  - purpose
  - inputs (with type and meaning)
  - outputs (with type and meaning)
  - constraints / invariants
- Keep interfaces explicit.
- Avoid monolithic scripts.
- Avoid duplicated business logic across training / evaluation / experiment scripts.
- CAPA-related logic (CAMA, DAPA, utility, constraints, revenue) should be self-contained modules reusable by both the heuristic CAPA runner and the RL-CAPA environment.

### 4) Full authority
You have full permission to:
- install missing packages with `pip install --break-system-packages` or `pip install`
- reorganize files
- create new modules, tests, configs, plots, docs, and scripts
- add logging, metrics, visualization, and experiment runners
- remove dead or misleading code that conflicts with the paper

### 5) No fake completeness
- Do not claim RL-CAPA exists if only CAPA exists.
- Do not claim "training supported" if there is no real replay buffer, target network, optimization loop, evaluation loop, and checkpointing.
- Do not claim "visualization supported" if reward/loss curves are not actually generated from real logs.

### 6) Git version control
All work MUST be tracked under git. Follow these conventions strictly:

#### Repository initialization
If the repository is not yet a git repo, initialize it:
```bash
git init
git add -A
git commit -m "init: original codebase before audit"
```

#### Branch strategy
- `main`: stable, verified code only
- `audit`: Phase 1–3 work (reading papers, auditing, writing reports)
- `feat/capa-repair`: Phase 4 CAPA repair and completion
- `feat/rl-capa`: Phase 5 RL-CAPA implementation
- `feat/visualization`: Phase 6 training curve and experiment plots
- `feat/experiments`: Phase 7 experiment suite
- `feat/reviewer-response`: reviewer-required experiments (sensitivity, ref[17], overhead)

Merge each feature branch into `main` only after verification passes.

#### Commit conventions
Use conventional commit prefixes:
- `init:` — repository initialization, original snapshot
- `docs:` — audit report, checklist, protocol, implementation notes
- `refactor:` — restructuring existing code without changing behavior
- `feat:` — new functionality (CAMA, DAPA, DDQN, env, etc.)
- `fix:` — correcting bugs or paper-inconsistent logic
- `test:` — adding or updating tests
- `experiment:` — experiment scripts, configs, result generation
- `plot:` — visualization and plotting code
- `config:` — adding or modifying YAML configs

Commit messages must be descriptive:
```
feat(cama): implement utility evaluator u(τ,c) per Eq.6
feat(dapa): add RVA second-lowest payment rule per Algorithm 3 Lines 22-24
feat(rl/env): implement joint training environment for M_b and M_m
fix(dapa): correct single-platform payment to use Eq.3 case |P_τ|=1
test(cama): add threshold split behavior verification
experiment: add sensitivity sweep for ω parameter
docs: write code audit report
```

#### Commit granularity
- Commit after completing each **sub-objective** (e.g., after implementing CAMA, after implementing DAPA, after each DDQN agent)
- Do NOT make a single giant commit per Phase
- Do NOT commit broken or untested code to `main`
- Every commit on `main` should pass existing tests

#### Tags and milestones
Tag each major milestone:
```bash
git tag -a v0.1-audit -m "Phase 1-3: audit complete, report generated"
git tag -a v0.2-capa -m "Phase 4: CAPA fully implemented and tested"
git tag -a v0.3-rl-capa -m "Phase 5: RL-CAPA training operational"
git tag -a v0.4-viz -m "Phase 6: training curves and plots generated"
git tag -a v0.5-experiments -m "Phase 7: full experiment suite complete"
git tag -a v1.0-final -m "All objectives met, final verification passed"
```

#### .gitignore
Create or update `.gitignore` to include:
```
__pycache__/
*.pyc
*.pyo
.eggs/
*.egg-info/
dist/
build/
.venv/
venv/
*.pt
*.pth
outputs/checkpoints/
outputs/logs/*.csv
wandb/
.ipynb_checkpoints/
```
Note: Do NOT ignore `outputs/plots/` — generated figures must be tracked.

#### Workflow integration
At the end of each Phase in the required workflow (see below), perform:
```bash
git add -A
git status  # review what changed
git commit -m "<prefix>: <descriptive message>"
```

Before starting a new Phase, verify the working tree is clean:
```bash
git status  # must show "nothing to commit, working tree clean"
```

---

## Source-of-truth documents

Use the following priority order:

1. `Auction-Aware_Crowdsourced_Parcel_Assignment_for_Cooperative_Urban_Logistics.md` (paper)
2. `MinerU_markdown_Competition_and_Cooperation_Global_Task_Assignment_in_Spatial_Crowdsourcing_2038811080154714112.md` (reference [17])
3. `review.md` (reviewer criticisms and required experiments)
4. current repository code
5. README / comments in code

If code and paper disagree, follow the paper.
If paper and review imply missing experiments, implement those experiments.

---

## Primary objectives

### Objective A — Audit the repository against CAPA
Perform a line-by-line and module-by-module audit of the current codebase and produce a written report answering:

1. Is the **full CAPA pipeline** implemented (Algorithm 1)?
   - batch accumulation (`Γ_S ← Γ_S ∪ Γ_t`)
   - batch trigger (`if t_cum == Δb`)
   - local courier retrieval (`C_S` from `C`)
   - cooperating platform retrieval (`P_S` from `P`)
   - CAMA local assignment (Algorithm 2)
   - construction of auction pool (`L_cr`)
   - DAPA dual-layer auction (Algorithm 3)
   - final matching plan composition (`M ← M ∪ M_lo ∪ M_cr`)
   - state reset after batch (`M_cr ← ∅, M_lo ← ∅, Γ_t ← ∅, t_cum = 0`)

2. Is **CAMA** implemented faithfully (Algorithm 2)?
   - feasibility checks: deadline (`c_j can reach l_τ_i before t_τ_i`) and capacity (`w_τ_i ≤ w̄_c_j`)
   - utility computation `u(τ, c)` per Eq. 6: `u(τ,c) = γ · Δw_τ + (1-γ) · Δd_τ`
     - capacity ratio: `Δw_τ = 1 - (Σw_ψ + Σw_τ) / w_c`
     - detour ratio: `Δd_τ = min_{1≤i≤|S_w|-1} π(l_i, l_{i+1}) / (π(l_i, l_τ) + π(l_τ, l_{i+1}))`
   - candidate set construction (`G`)
   - dynamic threshold `T_h` per Eq. 7: `T_h = ω · Σu(τ_i, c_j) / |M_t|`
   - split into local assignment `M_lo` (u ≥ T_h) vs auction pool `L_cr` (u < T_h or no feasible courier)

3. Is **DAPA / DLAM** implemented faithfully (Algorithm 3)?
   - first-layer FPSA among couriers within each cooperating platform
     - bid function Eq. 1: `B_F(c_P^i, τ) = p_min + (α · Δd_τ + β · g(c_P^i)) · γ · p'_τ`
     - winner: courier with highest `B_F` per platform
     - winning price Eq. 2: `p'(τ, c_win^P) = max{B_F(c_P^i, τ)}`
   - second-layer RVA among platforms
     - bid function Eq. 3: `B_R(P, τ) = p'(τ, c_win^P) + f(P)·μ_2·p_τ` (if |P_τ|≥2), or `p'(τ, c_win^P) + μ_2·p_τ` (if |P_τ|=1)
     - cooperation quality: `f(P) = Q̄_P^Loc / T_Loc`
     - winner: platform with lowest `B_R`
     - payment Eq. 4: `p'(τ, P_win) = min{B_R(P, τ) | P ∈ (P \ P_win)}` (second-lowest bid)
   - single-platform case: payment = `B_F(c_P_win^k, τ) + μ_2·p_τ` (Line 27 of Algorithm 3)
   - upper-limit / payment constraints

4. Are the equations from the paper reflected correctly?
   - Eq. 1: FPSA bid function
   - Eq. 2: FPSA winning price
   - Eq. 3: RVA bid function (two cases)
   - Eq. 4: RVA payment (second-lowest)
   - Eq. 5: Revenue function `Rev_S(Γ_L, C_L, P)`
   - Eq. 6: Utility evaluator `u(τ, c)`
   - Eq. 7: Dynamic threshold `T_h`

5. Are all core experimental metrics reproducible?
   - total revenue (TR) per Eq. 5
   - completion rate (CR): ratio of completed tasks to total
   - batch processing time (BPT): wall-clock per batch

6. What is missing, inconsistent, stubbed out, incorrect, or only partially implemented?

#### Required output
Create:
- `docs/code_audit_report.md`

This report must include:
- file-by-file mapping from paper modules to source files
- missing logic list
- incorrect logic list
- proposed repair plan
- acceptance checklist

---

### Objective B — Repair and complete CAPA
If CAPA is incomplete or inconsistent, implement it completely and cleanly.

#### Required CAPA components
Create or refactor into clear modules such as:

- `src/core/entities.py` — Parcel, Courier, Platform, Station dataclasses
- `src/core/constraints.py` — feasibility checks (deadline, capacity, invariable)
- `src/core/revenue.py` — Eq. 5 revenue calculation, local payment `Rc(τ,c) = ζ·p_τ`
- `src/core/schedule.py` — courier schedule `L_c`, optimal insertion position
- `src/capa/utility.py` — Eq. 6 utility evaluator, Eq. 7 dynamic threshold
- `src/capa/cama.py` — Algorithm 2 CAMA
- `src/capa/dapa.py` — Algorithm 3 DAPA (FPSA + RVA)
- `src/capa/capa_runner.py` — Algorithm 1 CAPA framework
- `src/capa/bid_functions.py` — Eq. 1, Eq. 2, Eq. 3, Eq. 4
- `src/capa/utils.py`

You may adapt file names to the repository structure, but the modular decomposition must remain explicit.

#### Required implementation details

##### CAMA (Algorithm 2, Section 3.2)
Implement:
- feasible courier search for each parcel: deadline and capacity checks
- utility evaluator `u(τ, c)` per Eq. 6
  - `Δw_τ = 1 - (Σ_{ψ∈Ψ_c} w_ψ + Σ_{τ∈Γ_c} w_τ) / w_c`
  - `Δd_τ = min_{1≤k≤|L_c|-1} π(l_k, l_{k+1}) / (π(l_k, l_τ) + π(l_τ, l_{k+1}))`
  - `u(τ, c) = γ · Δw_τ + (1-γ) · Δd_τ`
- candidate set construction `G`: for each parcel, select (τ_i, c_j) with max utility
- dynamic threshold `T_h` per Eq. 7 using ALL feasible pairs `M_t`, not just candidates
- output:
  - local assignment `M_lo`: pairs where `u(τ, c) ≥ T_h`
  - auction pool `L_cr`: parcels where `u(τ, c) < T_h` OR no feasible courier

##### DAPA / DLAM (Algorithm 3, Section 3.3)
Implement:
- parcel broadcast abstraction: each parcel in `L_cr` is broadcast to all cooperating platforms
- internal FPSA for each cooperating platform (Lines 4–15):
  - for each platform P_j, iterate over its couriers
  - check feasibility for (c_P_j^k, τ_i)
  - compute bid `B_F(c_P_j^k, τ_i)` per Eq. 1
  - select highest-bidding courier as internal winner
  - record (c_P_j^k, τ_i, P_j, B_F) in `B_τ_i`
- platform-level bid construction via RVA (Lines 17–28):
  - if `|B_τ_i| ≥ 2`: compute `B_R(P_j, τ_i)` per Eq. 3, sort ascending, winner = lowest bid, payment = second-lowest bid
  - if `|B_τ_i| == 1`: payment = `B_F(c_P_win^k, τ_i) + μ_2 · p_τ`
- final cross-platform courier assignment `M_cr`

##### CAPA runner (Algorithm 1, Section 3.1)
Implement the full per-batch online loop:
- parcel stream accumulation (`Γ_S ← Γ_S ∪ Γ_t`)
- trigger on batch size (`t_cum == Δb`)
- retrieve available inner couriers `C_S` and cooperating platforms `P_S`
- call CAMA(Γ_S, C_S) → M_lo, L_cr
- call DAPA(P_S, L_cr) → M_cr
- merge: `M ← M ∪ M_lo ∪ M_cr`
- reset: `M_cr ← ∅, M_lo ← ∅, Γ_t ← ∅, t_cum = 0`
- **unassigned parcels**: per Section 3.2 ("parcels not allocated in the current batch will reenter the next batch for re-matching"), carry over unassigned parcels to `Γ_S` for the next batch

#### Required validation
Create:
- `tests/test_cama.py`
- `tests/test_dapa.py`
- `tests/test_capa_pipeline.py`

Tests must verify:
- feasibility logic (deadline and capacity)
- utility computation matches Eq. 6
- threshold computation matches Eq. 7
- threshold split behavior (u ≥ T_h → local, u < T_h → auction pool)
- FPSA winner selection (highest bid wins)
- RVA payment rule (second-lowest bid for ≥2 platforms, max price for 1 platform)
- end-to-end batch assignment consistency

---

### Objective C — Implement RL-CAPA strictly according to the paper

The repository currently appears to lack a real RL-CAPA implementation. Implement it from scratch if necessary.

## RL-CAPA scope (Section 3.4)
RL-CAPA is **not** a replacement for DAPA.
RL-CAPA learns two decision processes and still uses DAPA for actual cross-platform execution.
The two DDQN processes are **closely coupled** and **jointly trained** (see Discussion in Section 3.4).

### Stage 1: Batch-size partitioning MDP `M_b = (S_b, A_b, P_b, R_b)`
Implement a DDQN agent for selecting batch duration / time-window.

#### State space `S_b` (from paper Section 3.4)
```
s_t = (|Γ_t^Loc|, |C_t^Loc|, |D|, |T|)
```
where:
- `|Γ_t^Loc|`: number of pending parcels on the local platform
- `|C_t^Loc|`: number of available couriers on the local platform
- `|D|`: average distance between couriers and pick-up tasks
- `|T|`: task urgency relative to current time slice and task deadline

#### Action space `A_b` (from paper Section 3.4)
```
A_b = [h_L, h_{L+1}, ..., h_M]
```
A **discrete set of allowed batch sizes** (e.g., h_L=10, h_M=20 → actions {10,11,...,20}).
Each action `a_t ∈ A_b` represents a specific batch duration in seconds.

#### Reward function `R_b` (from paper Section 3.4)
```
R(s_{t+1} | s_t, a_t) = Rev_S(Γ_Loc, C_Loc, P)   # total matching revenue in the batch, Eq. 5
```
Expected cumulative reward:
```
E = Σ_{t=0}^{∞} γ^t · Rev_S^t(Γ_Loc, C_Loc, P)
```
where γ ∈ [0,1] is the discount factor (paper uses γ=0.9).

#### DDQN must include
- online Q network
- target Q network (separate, for action selection to mitigate overestimation bias)
- replay buffer
- epsilon-greedy exploration
- target network update schedule
- checkpointing

### Stage 2: Cross-or-not MDP `M_m = (S_m, A_m, P_m, R_m)`
Implement a DDQN agent for deciding whether each unassigned parcel enters the cross-platform auction pool or is deferred.

#### State space `S_m` (from paper Section 3.4)
```
s_m = (|ΔΓ|, t_τ, t_cur, Δb)
```
where:
- `|ΔΓ|`: number of unassigned parcels
- `t_τ`: parcel's deadline
- `t_cur`: current time
- `Δb`: batch size from M_b (coupling between the two MDPs)

#### Action space `A_m` (from paper Section 3.4)
```
a_m ∈ {0, 1}
```
- `a_m = 1`: assign parcel to cross-platform auction pool
- `a_m = 0`: defer parcel to next batch

#### Reward function `R_m` (from paper Section 3.4, Eq. 8)
```
R_m(s_m, a_m) = {
    p_τ - Rc(τ, c)        if a_m = 0 and I(τ) = 1   # local assignment revenue
    p_τ - p'(τ, c)        if a_m = 1 and I(τ) = 1   # cross-platform assignment revenue
    0                      otherwise                   # not assigned
}
```
where `I(·) ∈ {0, 1}` is a binary indicator (1 = successful allocation).

**Critical**: If parcel τ is not assigned (I(τ)=0), it reappears as a new agent in the next batch.

#### Centralized Q-network (from paper Section 3.4)
Since the number of parcels varies dynamically across batches, use a **centralized Q-network framework** where all parcel agents share a common Q-function that generalizes across varying parcel states and actions.

### Joint training loop (from paper Discussion in Section 3.4)
The paper states: "we jointly train the DDQN models for M_b and M_m. During joint training, the shared environment is updated based on the combined outcomes of both decision processes."

Implement a training loop that:
1. Observe environment state → construct `s_b`
2. Select batch size `a_b` using batch-size DDQN (epsilon-greedy)
3. Accumulate parcels for `a_b` time units
4. Retrieve available couriers and platforms
5. Run CAMA for local matching → get `M_lo` and unassigned set `ΔΓ`
6. For each unassigned parcel τ ∈ ΔΓ:
   - Construct parcel-level state `s_m = (|ΔΓ|, t_τ, t_cur, Δb=a_b)`
   - Select action `a_m` using cross-or-not DDQN (epsilon-greedy)
   - If `a_m = 1`: add τ to auction pool
   - If `a_m = 0`: defer τ to next batch
7. Send auction pool parcels to DAPA → get `M_cr`
8. Compute rewards:
   - `R_b` = total batch revenue (Eq. 5)
   - `R_m` for each parcel agent (per the reward function above)
9. Transition to next state
10. Store transitions in replay buffers for BOTH DDQNs
11. Sample mini-batches and optimize BOTH DDQNs
12. Periodically update target networks
13. Periodically evaluate policy performance without exploration

### RL hyperparameters (from paper Section 4.1)
- Optimizer: RMSprop
- Learning rate: 0.001
- Discount factor: γ = 0.9
- Use Double DQN (DDQN) to mitigate overestimation bias

#### Required files
Suggested structure:
- `src/rl/env.py` — RL environment wrapping the CAPA pipeline
- `src/rl/state_builder.py` — state construction for S_b and S_m
- `src/rl/replay_buffer.py` — experience replay buffer
- `src/rl/models.py` — Q-network architectures for batch-size and cross-or-not DDQNs
- `src/rl/ddqn_agent.py` — DDQN agent with target network, epsilon-greedy, optimization
- `src/rl/train_rl_capa.py` — joint training loop
- `src/rl/evaluate_rl_capa.py` — evaluation without exploration
- `src/rl/visualize.py` — training curve plotting

Adapt names if necessary, but preserve the separation of concerns.

#### Forbidden shortcuts
- No fake RL wrapper around heuristics
- No fixed policy labeled as DDQN
- No random search mislabeled as RL training
- No omission of target network or replay buffer if claiming DDQN
- No "offline direct computation" pretending to be environment interaction

---

## Objective D — Add RL training observability and visualization
The paper and codebase currently lack proper RL training visualization. Add full experiment logging and plotting.

### Required logging
For RL-CAPA training, record at minimum:
- episode return (total revenue per episode)
- moving-average return (e.g., 100-episode window)
- Q loss for batch-size DDQN
- Q loss for cross-or-not DDQN
- epsilon values
- average selected batch size per episode
- cross decision ratio (fraction of parcels sent to auction pool)
- completion rate per episode
- total revenue per episode
- batch processing time per episode
- evaluation return at periodic checkpoints

### Required outputs
Create:
- `outputs/plots/train_reward.png` — raw episode return over training
- `outputs/plots/train_reward_moving_avg.png` — smoothed return curve
- `outputs/plots/batch_ddqn_loss.png` — Q loss for batch-size DDQN
- `outputs/plots/cross_ddqn_loss.png` — Q loss for cross-or-not DDQN
- `outputs/plots/eval_revenue_curve.png` — evaluation revenue at checkpoints
- `outputs/plots/eval_completion_curve.png` — evaluation CR at checkpoints
- `outputs/plots/batch_size_policy_hist.png` — histogram of selected batch sizes
- `outputs/plots/cross_action_ratio.png` — cross-or-not action ratio over training
- `outputs/plots/epsilon_decay.png` — epsilon schedule over training

Also save raw CSV logs:
- `outputs/logs/train_metrics.csv`
- `outputs/logs/eval_metrics.csv`

If tensorboard or wandb is added, it is supplementary, not a substitute for static exported plots.

---

## Objective E — Reproduce and extend experiments required by the paper and reviewers
Implement a reproducible experiment suite that covers both the paper's existing evaluation and the missing reviewer-required studies.

### Baseline experiments to support (from paper Section 4)
At minimum, reproduce experiments varying:
- number of parcels `|Γ|` — NYTaxi: {0.5K, 2K, 5K, 10K, 20K}; Synthetic: {5K, 20K, 50K, 100K, 200K}
- number of couriers `|C|` — NYTaxi: {0.1K, 0.2K, 0.3K, 0.4K, 0.5K}; Synthetic: {1K, 2K, 3K, 4K, 5K}
- courier radius `rad` — {0.5, 1, 1.5, 2, 2.5} km
- number of cooperating platforms `|P|` — {2, 4, 8, 12, 16}

Compared methods: RL-CAPA, CAPA, RamCOM [6], MRA [21], Greedy [21]

### Reviewer-driven additions

#### R1-W2: Communication/computation overhead analysis
Add experiments or profiling for:
- per-batch runtime under varying `|P|`, `|Γ|`, `|C|`
- breakdown of runtime across:
  - local matching (CAMA)
  - FPSA
  - RVA
  - RL decision stages (state construction, DDQN forward pass)
- communication proxy: message count between local and cooperating platforms per batch

Create:
- `outputs/plots/runtime_breakdown.png` — stacked bar chart of time per component
- `outputs/plots/runtime_vs_platforms.png`
- `outputs/plots/runtime_vs_parcels.png`
- `outputs/plots/runtime_vs_couriers.png`

#### R1-W5: Sensitivity analysis of manually chosen parameters
Add systematic sweeps for:
- sharing rate `μ_1` ∈ {0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7}
- sharing rate `μ_2` ∈ {0.1, 0.2, 0.3, 0.4} (subject to μ_1 + μ_2 ≤ 1)
- balance coefficient `γ` in utility Eq. 6 ∈ {0.1, 0.3, 0.5, 0.7, 0.9}
- dynamic threshold sensitivity factor `ω` in Eq. 7 ∈ {0.2, 0.4, 0.6, 0.8, 1.0, 1.2}
- local courier payment ratio `ζ` (Rc(τ,c) = ζ·p_τ) ∈ {0.1, 0.2, 0.3, 0.4, 0.5}
- cooperating platform sharing rate (FPSA parameter `γ` in Eq. 1) ∈ {0.1, 0.3, 0.5, 0.7, 0.9}

At minimum produce for each parameter sweep:
- TR vs parameter value
- CR vs parameter value
- BPT vs parameter value

Create:
- `outputs/plots/sensitivity_mu1.png`
- `outputs/plots/sensitivity_mu2.png`
- `outputs/plots/sensitivity_gamma_utility.png`
- `outputs/plots/sensitivity_omega.png`
- `outputs/plots/sensitivity_zeta.png`
- `outputs/plots/sensitivity_gamma_fpsa.png`

#### R2-1 & R2-2: Comparison with reference [17]
Reviewer 2 requires:
- Clear discussion of differences between this work and [17] (Li et al., "Competition and Cooperation: Global Task Assignment in Spatial Crowdsourcing")
- Addition of [17]'s methods (BaseGTA, ImpGTA) as baselines

Implementation requirements:
- Read the reference [17] paper thoroughly from the project files
- Implement BaseGTA and ImpGTA as baseline algorithms (or faithful approximations)
- Add them to the experiment suite alongside RamCOM, MRA, Greedy
- Create comparison plots: TR, CR, BPT across all parameter variations
- Create `docs/comparison_with_ref17.md` documenting the key differences

#### R2-3: RL training details
Add explicit reporting of:
- training time (wall clock)
- number of training episodes
- dataset partition / training split / evaluation split
- checkpoint interval
- hardware / package versions
- convergence behavior

Create:
- `outputs/tables/rl_training_summary.csv`

#### R3-3: RL-CAPA interaction visualization
Add a visualization showing the bidirectional dependency between M_b and M_m:
- How batch size affects the number/urgency of parcels in M_m
- How cross-or-not decisions affect future states in M_b
- Create `outputs/plots/rl_capa_interaction.png`

#### Cross-platform number effect (explicit)
This must be explicitly runnable and plotted:
- effect of `|P|` on TR / CR / BPT for RL-CAPA, CAPA, RamCOM
- Create `outputs/plots/platform_count_effect.png`

### Experiment runner
Create:
- `scripts/run_experiments.py` with `--suite paper_main` and `--suite reviewer_supplement`
- Each experiment writes results to `outputs/results/` as CSV
- Plotting scripts read from CSV and generate figures

---

## Objective F — Dataset protocol and training/evaluation split
The paper text is unclear about RL training data usage. You must make the protocol explicit and reproducible.

### Required protocol
Document and implement:
- dataset loading (NYTaxi from https://www.nyc.gov, Synthetic from Shanghai logistics data)
- preprocessing: random parcel weight assignment from U(0,10), deadline from 0.5–24 hours
- random seeds for reproducibility
- train / validation / test split (and whether temporal or random)
- how parcel streams are generated from raw data (arrival sequence based on order of appearance)
- whether courier/platform states are reset per episode
- how synthetic data is generated and parameterized
- road network construction from OpenStreetMap (Shanghai: 216,225 edges, 14,853 nodes; NYC: 8,635,965 edges, 157,628 nodes)
- courier preference coefficients `α` and `β` generation: uniform distribution

Create:
- `docs/data_protocol.md`

Also ensure every experiment script writes:
- dataset name
- split name
- seed
- config hash
- timestamp

---

## Objective G — Deliver reproducible CLI entry points
Provide explicit commands for:

### Audit
```bash
python -m scripts.audit_codebase
```

### Run CAPA baseline
```bash
python -m scripts.run_capa --config configs/capa/default.yaml
```

### Train RL-CAPA
```bash
python -m scripts.train_rl_capa --config configs/rl_capa/default.yaml
```

### Evaluate RL-CAPA
```bash
python -m scripts.eval_rl_capa --config configs/rl_capa/default.yaml --checkpoint path/to/checkpoint.pt
```

### Run paper-style experiment suite
```bash
python -m scripts.run_experiments --suite paper_main
```

### Run reviewer supplement suite
```bash
python -m scripts.run_experiments --suite reviewer_supplement
```

### Run sensitivity analysis
```bash
python -m scripts.run_experiments --suite sensitivity
```

### Run reference [17] comparison
```bash
python -m scripts.run_experiments --suite ref17_comparison
```

---

## Required project outputs

By the end of the work, the repository must contain at least:

### Documentation
- `docs/paper_spec_checklist.md`
- `docs/code_audit_report.md`
- `docs/data_protocol.md`
- `docs/implementation_notes.md`
- `docs/experiment_manifest.md`
- `docs/comparison_with_ref17.md`

### Code
- complete CAPA modules (entities, constraints, revenue, CAMA, DAPA, runner)
- complete RL-CAPA modules (env, state_builder, replay_buffer, models, ddqn_agent, train, evaluate, visualize)
- tests
- experiment runners
- plotting utilities
- baseline implementations (RamCOM, MRA, Greedy, BaseGTA, ImpGTA)

### Configs
- `configs/capa/default.yaml`
- `configs/rl_capa/default.yaml`
- `configs/experiments/paper_main.yaml`
- `configs/experiments/reviewer_supplement.yaml`
- `configs/experiments/sensitivity.yaml`
- `configs/experiments/ref17_comparison.yaml`

### Outputs
- plots (all listed above)
- CSV logs
- model checkpoints
- experiment summary tables

---

## Acceptance criteria

The task is not complete unless all of the following are true:

1. CAPA can be run end-to-end from the command line, producing TR/CR/BPT.
2. RL-CAPA can actually train with DDQN (joint training of M_b and M_m).
3. RL training produces real reward/loss curves (not fake or random data).
4. Experiment scripts reproduce paper-style comparisons across all parameter variations.
5. Reviewer-requested parameter sensitivity experiments are added (R1-W5).
6. Communication/overhead analysis is added (R1-W2).
7. Reference [17] methods are implemented and compared (R2-1, R2-2).
8. RL training details are reported (R2-3).
9. Code audit report explicitly states what was missing and what was repaired.
10. No forbidden fallback / degradation logic was introduced.
11. Tests pass.
12. The repository documentation is sufficient for another researcher to reproduce the main results.
13. Git history has meaningful commits per phase, with conventional commit messages.
14. A `v1.0` tag exists on the final verified commit.

---

## Version control (Git)

Git is mandatory throughout the entire workflow. Every phase must produce at least one commit. This ensures traceability, enables rollback, and documents the development process.

### Git initialization
If the repository is not already a git repo, initialize it at the start:
```bash
git init
echo "__pycache__/\n*.pyc\n.env\noutputs/logs/\noutputs/checkpoints/\n*.egg-info/\n.eggs/\ndist/\nbuild/\n.venv/\nnode_modules/" > .gitignore
git add .gitignore CLAUDE.md agent.md
git commit -m "chore: initialize repository with CLAUDE.md and agent.md"
```

### Commit discipline
- **One commit per logical unit of work.** Do not bundle unrelated changes.
- **Commit messages follow conventional commits:**
  - `feat:` new feature or algorithm implementation
  - `fix:` bug fix or correction against the paper
  - `refactor:` restructure without changing behavior
  - `test:` add or update tests
  - `docs:` documentation only
  - `chore:` tooling, config, gitignore, dependency management
  - `experiment:` experiment scripts or results
- **Commit message must reference the phase and objective**, e.g.:
  - `docs(phase1): create paper_spec_checklist.md`
  - `docs(phase3): create code_audit_report.md`
  - `feat(phase4): implement CAMA algorithm per Algorithm 2`
  - `feat(phase4): implement DAPA algorithm per Algorithm 3`
  - `feat(phase5): implement batch-size DDQN agent for M_b`
  - `feat(phase5): implement cross-or-not DDQN agent for M_m`
  - `feat(phase5): implement joint training loop for RL-CAPA`
  - `test(phase4): add CAMA and DAPA unit tests`
  - `experiment(phase7): run sensitivity analysis for mu1, mu2`

### Branching strategy
- **`main`**: stable, all tests pass, all phases completed
- **`dev`**: active development branch, commit frequently here
- **Phase branches (optional but recommended for large changes):**
  - `phase4/repair-capa`
  - `phase5/implement-rl-capa`
  - `phase7/experiments`
- Merge to `dev` after each phase is verified. Merge `dev` to `main` after Phase 8.

```bash
git checkout -b dev
# ... work on Phase 4 ...
git add -A && git commit -m "feat(phase4): implement CAMA per Algorithm 2"
# ... continue ...
```

### Required commits per phase
| Phase | Minimum commits | Example messages |
|-------|----------------|-----------------|
| Phase 1 | 1 | `docs(phase1): create paper_spec_checklist.md` |
| Phase 2 | 1 | `docs(phase2): map repository structure to paper` |
| Phase 3 | 1 | `docs(phase3): create code_audit_report.md` |
| Phase 4 | 3+ | `feat: implement entities`, `feat: implement CAMA`, `feat: implement DAPA`, `feat: implement CAPA runner`, `test: add CAPA tests` |
| Phase 5 | 4+ | `feat: implement RL env`, `feat: implement DDQN agents`, `feat: implement joint training`, `feat: implement evaluation` |
| Phase 6 | 1+ | `feat: add RL training visualization` |
| Phase 7 | 2+ | `experiment: run paper_main suite`, `experiment: run reviewer_supplement suite` |
| Phase 8 | 1 | `chore(phase8): final verification, update docs` |

### Tagging
After completing all phases, tag the release:
```bash
git tag -a v1.0 -m "Complete implementation: CAPA + RL-CAPA + experiments"
```

### What NOT to commit
- Large dataset files (add to `.gitignore`)
- Model checkpoint binaries over 50MB (use `.gitignore` or git-lfs)
- Temporary debug scripts
- IDE-specific files (.vscode/, .idea/)

### Recovery
If a phase introduces a regression, revert to the last known-good commit:
```bash
git log --oneline  # find the good commit
git revert <bad-commit-hash>
# or for a hard reset:
git reset --hard <good-commit-hash>
```

---

## Required workflow

Follow this exact workflow. **Commit after each phase.**

### Phase 1 — Read papers and reviews (Superpowers)
- Read the full paper markdown file, extracting all equations, algorithms, MDP definitions
- Read reference [17] markdown file, understanding BaseGTA, ImpGTA, AIM
- Read `review.md`, mapping each concern to an implementation task
- Create `docs/paper_spec_checklist.md`
- **Git:** `git add docs/paper_spec_checklist.md && git commit -m "docs(phase1): create paper_spec_checklist.md"`

### Phase 2 — Inspect repository
- inspect repository structure
- map code to paper sections
- identify missing modules and broken claims
- **Git:** commit any notes or mapping documents

### Phase 3 — Audit report
- write `docs/code_audit_report.md`
- do not implement before the audit report is clear
- **Git:** `git add docs/code_audit_report.md && git commit -m "docs(phase3): create code_audit_report.md"`

### Phase 4 — Repair CAPA
- fix architecture
- implement missing CAMA/DAPA/CAPA pieces
- extract CAPA logic into reusable modules (these will be called by RL-CAPA's env)
- add tests
- verify CAPA runs end-to-end
- **Git:** commit after each major module (entities, CAMA, DAPA, runner, tests). At minimum:
  ```bash
  git add src/core/ && git commit -m "feat(phase4): implement core entities, constraints, revenue"
  git add src/capa/cama.py && git commit -m "feat(phase4): implement CAMA per Algorithm 2"
  git add src/capa/dapa.py && git commit -m "feat(phase4): implement DAPA per Algorithm 3"
  git add src/capa/capa_runner.py && git commit -m "feat(phase4): implement CAPA framework per Algorithm 1"
  git add tests/ && git commit -m "test(phase4): add CAMA, DAPA, CAPA pipeline tests"
  ```

### Phase 5 — Implement RL-CAPA
- implement environment wrapping the CAPA pipeline
- implement two DDQN agents (batch-size and cross-or-not)
- implement joint training loop
- implement evaluation
- implement logging and checkpointing
- verify RL-CAPA trains and produces non-trivial rewards
- **Git:** commit after each component:
  ```bash
  git add src/rl/env.py src/rl/state_builder.py && git commit -m "feat(phase5): implement RL environment and state builder"
  git add src/rl/models.py src/rl/ddqn_agent.py src/rl/replay_buffer.py && git commit -m "feat(phase5): implement DDQN agents with replay buffer"
  git add src/rl/train_rl_capa.py && git commit -m "feat(phase5): implement joint training loop for M_b and M_m"
  git add src/rl/evaluate_rl_capa.py && git commit -m "feat(phase5): implement RL-CAPA evaluation"
  ```

### Phase 6 — Visualization
- add training curve plots
- add experiment result plots
- **Git:** `git commit -m "feat(phase6): add RL training visualization and plotting utilities"`

### Phase 7 — Experiments
- reproduce baseline experiments
- add reviewer-required experiments (sensitivity, overhead, ref [17] comparison)
- export figures and tables
- **Git:** commit after each experiment suite:
  ```bash
  git commit -m "experiment(phase7): run paper_main baseline experiments"
  git commit -m "experiment(phase7): run sensitivity analysis (R1-W5)"
  git commit -m "experiment(phase7): run ref[17] comparison (R2-1, R2-2)"
  git commit -m "experiment(phase7): run overhead analysis (R1-W2)"
  ```

### Phase 8 — Final verification
- run tests
- run one smoke training job (e.g., 50 episodes)
- run one full evaluation job
- confirm all required output files exist
- update docs
- **Git:**
  ```bash
  git commit -m "chore(phase8): final verification, all tests pass"
  git tag -a v1.0 -m "Complete: CAPA + RL-CAPA + experiments + reviewer responses"
  ```

---

## Coding standards

### Function-level documentation
Every public function must have a docstring in this style:

```python
def example_fn(arg1: int, arg2: float) -> float:
    """
    Compute ...

    Args:
        arg1: description of arg1
        arg2: description of arg2

    Returns:
        description of return value

    Raises:
        ValueError: when ...

    Notes:
        Implements Eq. X from the paper.
    """
```

### Typing
- Use type annotations where reasonable.
- Prefer dataclasses for entities/config bundles.

### Logging
- Use structured logging (`logging` module).
- Never swallow exceptions silently.
- Never convert hard failures into silent warnings if they break algorithmic validity.

### Determinism
- Set and log random seeds (Python, NumPy, PyTorch).
- Ensure reproducible evaluation.
- Use `torch.manual_seed()`, `np.random.seed()`, `random.seed()`.

### Module decomposition
- CAPA components (CAMA, DAPA, utility, constraints) must be independent modules importable by both `capa_runner.py` and `rl/env.py`.
- Avoid copy-pasting CAPA logic into RL code. The RL environment should import and call CAPA modules directly.

---

## What to do when the paper is ambiguous

Use the following resolution order:
1. equations (Eq. 1–7, reward functions)
2. algorithm pseudocode (Algorithms 1–3)
3. surrounding textual explanation (Sections 3.1–3.4)
4. experimental setup text (Section 4.1)
5. examples in the paper (Examples 1–4)
6. reviewer concerns as implementation guidance

If ambiguity still remains:
- document it in `docs/implementation_notes.md`
- choose the interpretation closest to the paper's literal wording
- do not hide the decision

---

## Final deliverable summary to print at the end
At the end of the task, produce a concise summary containing:
- audited gaps found
- files added / modified
- CAPA status (complete / partial)
- RL-CAPA status (complete / partial)
- plots generated
- experiments completed
- reviewer concerns addressed
- unresolved ambiguities, if any

Do not overstate completeness. Only report what was actually implemented and verified.