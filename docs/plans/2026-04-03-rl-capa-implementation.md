# RL-CAPA Implementation Plan

Date: 2026-04-03
Branch: `feat/rl-capa`

## Goal

Implement paper-faithful RL-CAPA on top of the existing Chengdu unified environment, following:

- `docs/Auction-Aware Crowdsourced Parcel Assignment for Cooperative Urban Logistics.md`
- `docs/rl_capa_algo.md`

The implementation must:

- keep CAMA and DAPA logic unchanged as the heuristic decision core
- learn only the two RL decision layers:
  - `M_b`: batch-size selection
  - `M_m`: cross-or-not decision for parcels in `L_cr`
- reuse the existing Chengdu simulation progression logic instead of reimplementing movement
- provide real DDQN components, replay buffers, target networks, and train/evaluate entrypoints

## Constraints

- no fallback logic
- no fake RL wrappers
- all functions must have docstrings
- all public functions must have type annotations
- environment code must import and reuse CAPA modules rather than copy-paste them

## Implementation slices

### Slice 1: RL package skeleton and tests

Create the package layout:

- `rl_capa/__init__.py`
- `rl_capa/config.py`
- `rl_capa/state.py`
- `rl_capa/transitions.py`
- `rl_capa/env.py`
- `rl_capa/ddqn/__init__.py`
- `rl_capa/ddqn/networks.py`
- `rl_capa/ddqn/replay_buffer.py`
- `rl_capa/ddqn/agent.py`
- `rl_capa/train.py`
- `rl_capa/evaluate.py`

Add tests first for:

- state construction for `S_b` and `S_m`
- replay buffer behavior
- DDQN target computation
- RL environment step semantics
- training loop smoke behavior
- evaluation output shape

Planned commit:

- `test(rl): add failing tests for rl-capa environment and ddqn`

### Slice 2: RL environment and state construction

Implement an RL environment wrapper over the unified Chengdu environment.

Core responsibilities:

- reset a seeded Chengdu episode
- expose `S_b`
- execute `a_b` to accumulate one batch
- run CAMA over the batch
- expose parcel-level `S_m` for each parcel in `L_cr`
- apply `a_m` decisions:
  - `1`: send to DAPA
  - `0`: defer to carry-over pool
- run DAPA on selected parcels
- update environment state and deferred parcels
- compute:
  - `R_b` from Eq. 5
  - `R_m` from the paper's three-branch definition
- return transitions for both `M_b` and `M_m`

Important design choice:

- `a_m = 0` uses the paper-consistent immediate reward `0`, and the deferred parcel reappears in the next batch as a new decision item

Planned commit:

- `feat(rl/env): implement shared rl-capa environment for M_b and M_m`

### Slice 3: DDQN components

Implement:

- batch Q-network for `M_b`
- parcel Q-network for `M_m`
- replay buffer
- online / target networks
- epsilon-greedy action selection
- DDQN update rule
- hard target synchronization

Default hyperparameters from the paper:

- optimizer: RMSprop
- learning rate: `0.001`
- discount factor: `0.9`

Repository defaults for unspecified parameters:

- replay capacity: `50_000`
- batch size: `64`
- target update interval: `100`
- epsilon start: `1.0`
- epsilon end: `0.01`

Planned commit:

- `feat(rl/ddqn): implement ddqn agents, networks, and replay buffers`

### Slice 4: Joint training loop

Implement joint training in `rl_capa/train.py`.

Responsibilities:

- build seeded environment episodes
- instantiate both DDQN agents
- jointly collect transitions from both decision processes
- optimize both agents during the same episode
- log:
  - episode return
  - `M_b` loss
  - `M_m` loss
  - epsilon values
  - completion / revenue metrics
- save checkpoints

Output artifacts:

- JSON metrics log
- model checkpoints

Planned commit:

- `feat(rl/train): implement joint rl-capa training loop`

### Slice 5: Evaluation and runner integration

Implement evaluation in `rl_capa/evaluate.py`.

Responsibilities:

- load trained checkpoints
- run deterministic evaluation episodes
- output normalized metrics:
  - `TR`
  - `CR`
  - `BPT`
  - delivered / accepted counts
- optionally persist batch traces for experiment scripts

Integrate into the unified runner:

- add `algorithms/rl_capa_runner.py`
- wire `rl-capa` into `algorithms/registry.py`

Planned commit:

- `feat(rl/eval): add rl-capa evaluation and unified runner integration`

### Slice 6: Documentation and verification

Update:

- `docs/implementation_notes.md`
- `README.md`

Verification:

- targeted RL tests
- runner smoke tests
- import checks

Planned commit:

- `docs(rl): document rl-capa environment, training, and evaluation`

## Open implementation boundaries

- The paper does not fully specify the exact neural network width/depth, replay size, target update interval, or epsilon schedule; these will be documented as repository defaults rather than paper claims.
- The current repository has a legacy `Greedy` runner with aggregate metrics only; RL-CAPA evaluation will compare against unified metrics, but RL implementation itself will not depend on that legacy code.
