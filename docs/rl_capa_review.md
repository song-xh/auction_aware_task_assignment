# RL-CAPA Implementation Review

Review date: 2026-04-03  
Reviewer: automated analysis against paper and `docs/rl_capa_algo.md`

---

## A. Environment Integration with the Main Project

**Status: PASS — full integration, no reimplementation**

- `rl_capa/env.py` lines 10–12 import `run_cama`, `run_dapa`, and `compute_total_revenue` directly from the canonical CAPA modules. No logic is duplicated.
- `_run_local_matching()` (lines 286–307) calls `run_cama()` with the correct arguments: parcels, couriers, travel model, config, current time, and service radius.
- `_run_cross_matching()` (lines 309–354) calls `run_dapa()` with the selected parcels and cooperating platforms.
- Couriers are converted via `legacy_courier_to_capa()` (line 263–266) and partner platforms via `legacy_platform_to_capa()` (lines 317–326), both reusing the canonical conversion functions.
- Parcels are converted via `legacy_task_to_parcel()` (line 138), which maps dataset fields to the CAPA `Parcel` dataclass.
- The double-auction mechanism (CAMA for local, DAPA for cross-platform) is fully preserved.

---

## B. Parcel Generation / Dataset Reading

**Status: PASS — parcels read from dataset and introduced sequentially by release time**

- Tasks are loaded from `self._environment.tasks` (the Chengdu environment seed), sorted by `(s_time, d_time, num)` at lines 67–71 — identical ordering to the main environment.
- Lines 103–110: batch accumulation only includes tasks where `task_arrival < batch_end_time`, using `_next_task_index` as a cursor into the sorted task list. Parcels are **not** all instantiated at t=0.
- `legacy_task_to_parcel()` (`env/chengdu.py` lines 274–283) correctly maps:
  - `parcel_id` ← `task.num`
  - `location` ← `task.l_node` (origin node)
  - `arrival_time` ← `task.s_time` (release time)
  - `deadline` ← `task.d_time`
  - `weight` ← `task.weight`
  - `fare` ← `task.fare`
- `_build_current_batch_state()` (lines 252–276) further restricts the auction pool to tasks whose arrival time ≤ `current_time`, ensuring strictly sequential introduction consistent with the paper's time-driven model.

---

## C. DDQN Components

**Status: PASS — Double DQN correctly implemented**

### State representation (`rl_capa/state.py`)

- **Batch state S_b** (lines 13–54): 4-dimensional vector `[pending_count, available_courier_count, avg_distance, avg_urgency]`.
  - `avg_urgency` uses `(deadline - now) / deadline` per paper reference [22].
- **Parcel state S_m** (lines 57–83): 4-dimensional vector `[|ΔΓ|, t_τ, t_cur, Δb]`.
  - `Δb` (batch size) is included to couple M_m to M_b, matching the paper's hierarchical MDP design.

### Action space

- **A_b** (`rl_capa/config.py` lines 22–43): discrete set `[h_L, …, h_M]` (batch durations in seconds).
- **A_m** (`rl_capa/ddqn/agent.py` line 63): binary — 0 = defer, 1 = cross-platform.

### Reward function (`rl_capa/env.py`)

- **R_b** (line 199): `compute_total_revenue([*local_assignments, *cross_assignments])` — equals Equation 5 of the paper.
- **R_m** three branches:
  - `a_m = 1`, DAPA assigns: `reward = assignment.local_platform_revenue` (lines 179–189).
  - `a_m = 1`, DAPA fails: parcel deferred to carry pool; reward resolved later (lines 191–197).
  - `a_m = 0`: parcel deferred; reward = 0 immediately, backfilled when assigned in a future batch (lines 165–171).
- Terminal resolution (`_resolve_pending_parcel_transitions()`, lines 356–407) correctly backfills deferred transitions.

### Replay buffer (`rl_capa/ddqn/replay_buffer.py`)

- Lines 14–64: bounded deque (`maxlen=capacity`), uniform sampling. Separate buffers for batch agent and cross agent (`rl_capa/train.py` lines 71–72).

### Target network (`rl_capa/ddqn/agent.py`)

- Lines 65–70: target network cloned from online network and set to eval mode.
- `maybe_update_target()` (lines 120–124): hard copy every `target_update_interval` steps.

### Double DQN update rule (lines 182–203)

```python
# Action selection uses ONLINE network
next_actions = torch.argmax(self.online_network(next_states), dim=1, keepdim=True)
# Value evaluation uses TARGET network
next_q = self.target_network(next_states).gather(1, next_actions).squeeze(1)
targets = rewards + (1.0 - dones) * self._discount_factor * next_q
```

This is the correct Double DQN formulation (not vanilla DQN).

### Hyperparameters (`rl_capa/config.py` lines 79–89)

RMSprop optimizer, learning rate 0.001, discount factor 0.9 — consistent with paper Section 4.1.

---

## D. Training Script

**Status: PASS — entry point exists and loop matches algorithm pseudocode**

- `rl_capa/train.py`: `train_rl_capa()` (lines 21–39) accepts environment seed, CAPA config, RL config, training config, and output directory.
- Batch agent: state_dim=4, action_dim=`len(batch_action_values())` (lines 51–60).
- Cross agent: state_dim=4, action_dim=2 (lines 61–70).
- Training loop (lines 78–116) follows the joint M_b / M_m structure from `docs/rl_capa_algo.md` Section 6:
  1. M_b selects batch duration → `environment.start_batch()`.
  2. Resolved pending transitions from prior batch are pushed to the cross buffer.
  3. M_m selects cross-or-defer per parcel → `environment.apply_parcel_actions()`.
  4. Batch and parcel transitions stored in respective buffers.
  5. Both agents train after warmup.
- Checkpoints: both agents saved to disk; episode returns and losses saved as JSON (lines 118–133).

---

## E. Evaluation

**Status: PASS — complete evaluation with all paper-defined metrics**

- `rl_capa/evaluate.py`: `evaluate_rl_capa()` (lines 19–81) loads agents from checkpoints and runs inference (`explore=False`).
- Metrics (lines 66–72):
  - **TR (Total Revenue)**: `compute_total_revenue(assignments)` — canonical implementation in `capa/metrics.py` line 12.
  - **CR (Completion Rate)**: `len(assignments) / total_parcel_count()`.
  - **BPT (Batch Processing Time)**: wall-clock seconds around `agent.select_action()` calls only, excluding routing/insertion time.
- All three metrics match paper Section 4.1.
- JSON summary saved with algorithm name and metrics.

---

## F. CLI / Registry Integration

**Status: PASS — fully wired**

- `algorithms/registry.py` line 15: `"rl-capa"` listed in `SUPPORTED_ALGORITHMS`.
- `algorithms/rl_capa_runner.py`: `RLCAPAAlgorithmRunner` implements the `AlgorithmRunner` interface; `build_rl_capa_runner()` factory used by the dispatcher.
- `runner.py` lines 64–67: CLI args for `--min-batch-size`, `--max-batch-size`, `--step-seconds`, `--episodes`.
- `build_algorithm_kwargs()` (lines 83–89) correctly translates CLI args to runner kwargs.

---

## Summary

| Dimension | Result | Key evidence |
|-----------|--------|--------------|
| Environment integration (CAMA/DAPA) | PASS | Direct calls to `run_cama`, `run_dapa` — no reimplementation |
| Dataset preprocessing | PASS | Uses same task sort order and conversion functions as main env |
| Parcel generation — dataset fields | PASS | All six fields mapped correctly in `legacy_task_to_parcel()` |
| Parcel generation — sequential timing | PASS | `_next_task_index` cursor; tasks gated by `task_arrival < batch_end_time` |
| State representation S_b, S_m | PASS | 4-dim vectors, correct features including coupling term Δb |
| Action spaces A_b, A_m | PASS | Discrete durations; binary cross-or-defer |
| Reward R_b | PASS | `compute_total_revenue()` over all assignments |
| Reward R_m | PASS | Three-branch with correct backfill for deferred parcels |
| Replay buffer | PASS | Bounded deque, uniform sampling, separate per agent |
| Target network | PASS | Hard update every `target_update_interval` steps |
| Double DQN update rule | PASS | Online net selects action, target net evaluates value |
| Hyperparameters | PASS | RMSprop, lr=0.001, γ=0.9 per paper |
| Training loop | PASS | Matches `docs/rl_capa_algo.md` Section 6 pseudocode |
| Evaluation | PASS | TR, CR, BPT all computed correctly |
| CLI integration | PASS | Registry, runner, and argument parsing all wired |

**No critical issues found.** The implementation faithfully follows the paper and algorithm description across all reviewed dimensions.
