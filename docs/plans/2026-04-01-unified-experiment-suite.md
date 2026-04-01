## Goal

Refactor the experiment orchestration so Chengdu experiments can be launched from one canonical entrypoint while preserving a single shared environment initialization for all comparisons at the same experimental point.

The implementation must satisfy these requirements:

- The canonical entrypoint remains the root `runner.py`.
- Paper metrics are the default outputs: `TR`, `CR`, `BPT`.
- Supported sweep axes include at least:
  - parcel count `|Γ|`
  - courier count `|C|`
  - service radius `rad`
  - cooperating platform count `|P|`
  - batch size / batch window
- Comparison experiments must run on the same environment seed and initialization.
- The unified Chengdu environment remains the only simulation truth source.
- No fallback logic is allowed.

## Current Gaps

1. `runner.py` only supports single-run execution.
2. `capa/experiments.py` still owns sweep and comparison helpers, which duplicates orchestration concerns outside the canonical CLI.
3. Current comparison helpers rebuild environments independently per algorithm and per run, so they do not guarantee identical initialization.
4. Experimental configuration is not centralized, making it easy for different algorithms to drift in their runtime setup.
5. The current environment object exposes the active simulation state, but not a stable snapshot/factory abstraction for repeated same-seed comparisons.

## Design Decision

Use `runner.py` as the user-facing canonical entrypoint, but keep the orchestration logic in a dedicated experiment package rather than turning `runner.py` into a monolithic script.

Recommended structure:

- `runner.py`
  - CLI only
  - exposes subcommands such as `run`, `sweep`, `compare`, `suite`
- `experiments/`
  - shared experiment dataclasses and validation
  - sweep orchestration
  - comparison orchestration
  - plotting and summary persistence
- `env/chengdu.py`
  - remains the only environment implementation
  - gains a resettable seed/snapshot abstraction for same-initialization replay
- `algorithms/`
  - remains responsible only for per-algorithm decision logic and algorithm-specific summaries

This keeps the user interface simple while keeping the orchestration testable and modular.

## Same-Environment Requirement

This is the core contract of the refactor.

For each sweep point:

1. Build one canonical Chengdu environment seed.
2. Freeze the initialization state needed for replay:
   - tasks and arrival ordering
   - station geometry and ranges
   - local courier objects and their initial routes/locations
   - partner platform courier objects and their initial routes/locations
   - platform parameters
3. For each algorithm in the comparison set:
   - clone the exact same seed into a fresh mutable environment instance
   - run the algorithm
   - record metrics and outputs

The comparison loop must never call the raw environment builder separately per algorithm.

## Proposed Modules

### `experiments/config.py`

Dataclasses for:

- single-run experiment config
- sweep config
- comparison config
- plot config

These configs must validate the paper-facing axes and prevent illegal combinations.

### `experiments/seeding.py`

Seed and snapshot abstractions for Chengdu:

- `ChengduEnvironmentSeed`
- `build_environment_seed(...)`
- `clone_environment_from_seed(...)`

The seed should contain only immutable or safely copyable initialization state.

### `experiments/sweep.py`

Reusable one-dimensional sweep orchestration:

- single algorithm over one axis
- fixed shared baseline config
- paper metrics summary and plots

### `experiments/compare.py`

Shared-environment comparison orchestration:

- multi-algorithm comparison at each sweep point
- guarantees one build per point and clone-per-algorithm execution
- persists comparison summaries and plots

### `experiments/plots.py`

Plot helpers for:

- metric-vs-parameter sweeps
- algorithm comparison plots

Plots should default to `TR`, `CR`, `BPT`.

## CLI Plan

Extend `runner.py` to support subcommands:

- `run`
  - single algorithm, single configuration
- `sweep`
  - single algorithm, one varying axis
- `compare`
  - multiple algorithms, one varying axis, same environment per point
- `suite`
  - paper-style collection of sweeps

Example direction:

```bash
python3 runner.py run --algorithm capa ...
python3 runner.py sweep --algorithm capa --axis num-parcels --values 100 200 500 ...
python3 runner.py compare --algorithms capa greedy basegta impgta --axis num-parcels --values 100 200 500 ...
python3 runner.py suite --suite paper-main --algorithms capa greedy basegta impgta
```

`rl-capa` can be accepted by the CLI but must continue to fail explicitly until implemented.

## Environment Refactor Plan

`env/chengdu.py` should be extended, not replaced.

Add:

- a canonical immutable seed/snapshot structure
- a clone path that recreates fresh mutable couriers/tasks/stations from the same initialization
- explicit environment metadata for experiment reporting

Do not mix algorithm-specific bookkeeping into the environment.

## Paper-Axis Coverage

The first complete suite should support these axes:

1. `num_parcels`
2. `local_couriers`
3. `service_radius`
4. `platforms`
5. `batch_size`

The experiment layer should map each axis cleanly to the environment or algorithm config:

- `num_parcels`: environment build limit
- `local_couriers`: environment seed composition
- `service_radius`: courier initialization / constraint parameter in the environment
- `platforms`: environment seed composition
- `batch_size`: algorithm run config

If `service_radius` is not yet externally configurable in the current environment path, expose that parameter explicitly rather than approximating it.

## Test Plan

Add tests before or alongside implementation for:

1. CLI dispatch
   - `runner.py run/sweep/compare/suite`
2. Same-seed guarantee
   - comparison point builds once
   - each algorithm gets a clone of the same initialization
3. Metric summary schema
   - `TR`, `CR`, `BPT` always present
4. Plot file naming and summary persistence
5. Axis mapping correctness
   - each sweep axis changes only the intended configuration field
6. Explicit `rl-capa` failure
   - compare/suite paths must fail clearly, not silently skip

## Commit Plan

Implement in small commits:

1. `docs(plan): add unified experiment suite plan`
2. `feat(experiments): add experiment config and environment seed abstractions`
3. `refactor(env): support deterministic environment cloning for comparisons`
4. `feat(experiments): add sweep and comparison orchestration`
5. `feat(cli): extend root runner with run/sweep/compare/suite subcommands`
6. `test(experiments): add shared-environment comparison coverage`
7. `docs(readme): document unified experiment commands`

## Acceptance Criteria

The refactor is complete when:

- `runner.py` is the canonical entrypoint for single runs and sweeps.
- Sweeps and comparisons produce paper metrics by default.
- Comparison runs reuse one initialization per sweep point and clone from that seed for each algorithm.
- The environment implementation remains centralized in `env/chengdu.py`.
- Old duplicate orchestration in `capa/experiments.py` is removed or reduced to a thin compatibility layer.
- Tests prove the same-environment guarantee.
