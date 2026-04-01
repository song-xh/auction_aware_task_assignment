## Goal

Implement two additional baselines and run the requested Chengdu experiment:

- `mra`
- `ramcom`

Then produce one large comparison on the unified Chengdu environment under:

- local couriers: `200`
- courier capacity: `50`
- courier service radius: `1km`
- cooperating platforms: `4`
- batch size: `300s`
- parcel counts: `1000`, `2000`, `3000`, `5000`
- algorithms: `capa`, `greedy`, `basegta`, `impgta`, `mra`, `ramcom`

Metrics required:

- `TR`
- `CR`
- `BPT`

The environment must remain shared and comparable across algorithms.

## Paper/Doc-Based Design Decisions

### MRA

The uploaded `docs/mra.md` describes MRA as:

- a single-platform auction-based multi-round assignment baseline
- based on a courier-parcel bipartite graph
- repeatedly assigning the current parcel-wise minimum-bid edges
- recomputing courier bids after each round as courier state changes

The same document explicitly allows an initial exact implementation without TS-Tree/TIL optimization.

Therefore:

- implement an exact candidate-graph version first
- use all feasible courier-parcel pairs in the current Chengdu state
- keep the multi-round commit / recompute loop faithful
- document that TS-Tree/TIL are not yet implemented as performance optimizations

### RamCOM

The uploaded `docs/ramcom.md` describes RamCOM as:

- online sequential processing
- inner-vs-outer worker choice by randomized threshold
- empirical acceptance sampling for outer workers
- cooperative pricing by maximizing expected cooperative revenue

The document also states that the original pricing routine depends on an external paper.

Therefore:

- implement RamCOM control flow faithfully
- implement the outer payment as an explicit searchable expected-revenue maximizer over candidate payment levels derived from worker history and request value
- document this as a repository-contained pricing realization, not as a claim that external paper [14] was separately reproduced

## Chengdu Environment Adaptation

### Shared environment constraint

All baselines must continue to run through `env/chengdu.py`.

No new standalone simulator is allowed.

### Capacity override

The requested large experiment uses courier capacity `50`.

The current Chengdu builder hard-codes capacity `75`.

Plan:

- expose courier capacity as a build parameter in the unified environment
- ensure that the same capacity is applied for all algorithms in a comparison point

### Service radius

The repository already interprets `service_radius` as:

- maximum shortest-path distance from courier current location to pickup location

This same constraint will be applied to:

- MRA local feasibility
- RamCOM inner-worker feasibility
- RamCOM outer-worker feasibility

### Courier history for RamCOM

RamCOM needs worker history to compute acceptance probabilities.

The Chengdu environment does not store explicit historical completed-request values.

Plan:

- derive worker history from the seeded legacy route at environment initialization
- use the seeded task fare values as the worker's historical completed values
- if a courier has an empty initial route, the history list remains empty and the acceptance model must handle this explicitly

This is an environment adaptation, not hidden fallback logic.

## Implementation Plan

### Step 1. Add tests first

Add failing tests for:

- MRA graph-round assignment behavior
- MRA recomputation after round commit
- RamCOM threshold branching
- RamCOM expected-payment search
- RamCOM outer acceptance sampling under deterministic random seed
- registry/runner exposure of `mra` and `ramcom`
- small comparison summary including the two new baselines

### Step 2. Implement baseline modules

Add:

- `baselines/mra.py`
- `baselines/ramcom.py`

Requirements:

- every function has a docstring
- explicit type hints on public functions
- no fallback-to-other-baseline behavior

### Step 3. Wire baselines into unified runner

Add:

- `algorithms/mra_runner.py`
- `algorithms/ramcom_runner.py`

Update:

- `algorithms/registry.py`
- `baselines/__init__.py`

### Step 4. Extend environment/config for experiment settings

Expose:

- courier capacity override
- worker history extraction for RamCOM

The same environment seed must still be cloned across algorithms at each comparison point.

### Step 5. Extend experiment comparison plotting

The current comparison flow writes summaries but not a generic multi-algorithm plot set.

Add generic plots for:

- `TR vs axis`
- `CR vs axis`
- `BPT vs axis`

for an arbitrary list of algorithms.

### Step 6. Verification ladder

1. unit tests
2. small deterministic smoke for `mra`
3. small deterministic smoke for `ramcom`
4. small shared-environment comparison across all six algorithms
5. only then the requested large comparison run

## Large Experiment Plan

Run one shared-environment comparison sweep over `num_parcels` with:

- `local_couriers=200`
- `courier_capacity=50`
- `service_radius=1.0`
- `platforms=4`
- `couriers_per_platform=50`
- `batch_size=300`
- `num_parcels in [1000, 2000, 3000, 5000]`
- `algorithms=[capa, greedy, basegta, impgta, mra, ramcom]`

Output:

- aggregate comparison summary JSON
- `TR vs num_parcels`
- `CR vs num_parcels`
- `BPT vs num_parcels`

## Monitoring Plan

The requested run may be long.

Use sparse supervision:

- short updates during implementation
- longer intervals during large experiment execution
- explicit reporting of whether slowness comes from:
  - legacy preprocessing
  - graph-based baseline logic
  - online cooperative matching logic

## Acceptance Criteria

This task is complete when:

- `mra` and `ramcom` are implemented under `baselines/`
- both are exposed through the unified root runner
- both pass small-scale environment-adaptation tests
- a small shared-environment experiment succeeds without pathological output like `CR=0` across the board
- the requested large sweep is executed
- plots and summaries are written
- any remaining approximation boundary is documented explicitly
