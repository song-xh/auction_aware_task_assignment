# 2026-04-07 CAPA Paper Audit

Scope:

- paper baseline: `docs/Auction-Aware Crowdsourced Parcel Assignment for Cooperative Urban Logistics.md`
- current runtime path: `algorithms/capa_runner.py -> env/chengdu.py -> capa/cama.py + capa/dapa.py`
- focus: CAPA parameters, service quality / preference terms, utility and revenue formulas, experiment flow, and CAPA runtime behavior

## Executive Verdict

The current repository is not in the same state as the older audit documents under `docs/`; the active CAPA path is now the unified `capa/* + env/chengdu.py` stack.

Current conclusions:

1. The current code has mostly implemented the paper's Eq.5/Eq.6/Eq.7 and the two-layer Eq.1-Eq.4 structure, but key paper parameters around courier preference and service quality are only shape-compatible, not paper-faithful.
2. The current feasibility model is still weaker than the paper because it does not model courier return deadline / full route deadline propagation.
3. The reported `BPT` metric is wrong for paper comparison because it excludes routing and insertion cost, which are the dominant CAPA runtime components.
4. CAPA being slow at `5000` parcels is only partly "reasonable". The algorithm is inherently heavy under exact road-network insertion search, but the current implementation has at least two additional problems that make the runtime worse or unstable:
   - graph loading is nondeterministic because DFS starts from an arbitrary `set` element
   - batch distance warmup performs exact shortest-path precomputation before feasibility filtering and dominates wall-clock runtime

## Findings

### 1. Critical: Chengdu graph loading is nondeterministic and can collapse to a tiny component

Evidence in code:

- `GraphUtils_ChengDu.py:230-235` builds the candidate node pool in a `set`
- `GraphUtils_ChengDu.py:332-335` converts the `set` to `list` and starts DFS from `nList[0]`

Because `set` iteration order is not stable, the DFS start node is unstable across processes. In repeated fresh imports of `GraphUtils_ChengDu`, the same map produced both:

- `After DFS nodeNumber: 1 | edgeNumber: 1`
- `After DFS nodeNumber: 36630 | edgeNumber: 50786`

This directly explains why some runs emit大量 `no paths suitable.` and become pathologically slow: the route graph may be reduced to a trivial connected component, after which many shortest-path queries fail.

Impact:

- correctness is nondeterministic
- runtime is nondeterministic
- experiment reproducibility is broken

### 2. Critical: the repository's `BPT` metric is not the paper's batch processing time

Evidence in code:

- `capa/metrics.py:22-24` defines `BPT` as `sum(report.timing.decision_time_seconds ...)`
- `capa/metrics.py:41-43` separately records excluded `routing`, `insertion`, and `movement`
- `capa/cama.py:166-174` explicitly subtracts routing/insertion/movement from `decision_time_seconds`
- `capa/dapa.py` uses the same timing accounting pattern

So the current `BPT` is not the end-to-end matching-round elapsed time described in the paper. It is a reduced metric after removing routing and insertion, exactly where CAPA spends most of its time.

Observed evidence:

- direct 20-parcel CAPA run: wall-clock `0.801s`
- same run's reported `BPT`: `0.0016604990050836932`

This is roughly a `480x` understatement.

Consequence:

- existing `result/exp_1/*/summary.json` BPT values are not comparable to the paper's claimed BPT
- current CAPA runtime is being visually underreported

### 3. High: service quality and preference parameters are not paper-faithful

Paper expectation:

- courier preference coefficients `alpha`, `beta` should be generated per courier
- courier quality term `g(c)` should come from historical `QS`, `ES`, `CS`
- platform cooperation quality `f(P)` should come from historical cross-platform quality

Current implementation:

- `capa/dapa.py:57-79` implements the Eq.1 structure with `alpha`, `beta`, `service_score`
- `capa/dapa.py:82-92` implements the Eq.3 structure with `historical_quality / max_quality`

But the actual parameter sources are synthetic constants:

- `env/chengdu.py:1033-1039` seeds all couriers with `preference=0.5`
- `Framework_ChengDu.py:47-50` sets `w=preference`, `c=1-preference`
- `env/chengdu.py:315-317` maps that into `alpha`, `beta`, and default `service_score=0.8`
- `env/chengdu.py:1074-1076` sets `platform_base_prices=1.0`, `platform_sharing_rates=0.4`, `platform_qualities={1.0, 0.9, 0.8, ...}`

In a direct environment probe, the active partner-courier parameters were:

- `alpha = 0.5` for every courier
- `beta = 0.5` for every courier
- `service_score = 0.8` for every courier
- `platform_qualities = {P1: 1.0, P2: 0.9, P3: 0.8, P4: 0.7}`

Verdict:

- formula shells exist
- paper-defined parameter semantics do not

### 4. High: CAMA / DAPA feasibility is still weaker than the paper constraints

Paper constraint expectation:

- capacity constraint
- pickup deadline
- drop-off deadline
- courier return deadline to station

Current code:

- `capa/models.py:38-51` courier model stores no courier deadline and no explicit drop-off deadlines
- `capa/cama.py:27-50` local feasibility only checks:
  - availability
  - current load + parcel weight
  - current location to pickup deadline
  - service radius
- `capa/dapa.py:31-54` cross feasibility uses the same reduced check

The current implementation does not verify whether inserting a new pickup into the remaining route preserves full-route feasibility against existing drop-off tasks and return-to-station deadline. That is a paper mismatch, not merely an optimization choice.

### 5. Medium: the utility and revenue formulas are materially closer to the paper than the old audit docs suggest

Current active path status:

- Eq.6 utility:
  - `capa/utility.py:76-80` capacity ratio
  - `capa/utility.py:166-194` utility
- Eq.7 threshold:
  - `capa/utility.py:197-202`
  - `capa/cama.py:145-148` computes threshold over all feasible pairs `M_t`
- Eq.5 revenue:
  - local: `capa/utility.py:44-56`
  - cross: `capa/utility.py:59-68`
  - DAPA assignment settlement: `capa/dapa.py:100-119`
- Eq.1-Eq.4 auction shape:
  - courier bid: `capa/dapa.py:57-79`
  - platform quality factor: `capa/dapa.py:82-92`
  - second-layer bid and second-lowest payment: `capa/dapa.py:210-239`

So the current unified code is materially better than the stale `docs/code_audit_report.md` and `docs/paper_spec_checklist.md`, which still describe the older `MyMethod/*` path.

### 6. Medium: the default "paper" experiment flow has drifted from the paper

Evidence:

- `experiments/paper_config.py:6-13` default algorithm list excludes `rl-capa`
- `experiments/paper_config.py:25-30` formal parcel sweep is `[1000, 2000, 3000, 5000]`, not the paper's NYTaxi / Synthetic parcel scales
- the active environment is Chengdu-only legacy simulation, not the paper's NYTaxi + Shanghai synthetic setup

Interpretation:

- the repository currently runs a Chengdu paper-style suite, not the paper's original experiment matrix
- this may still be useful for local regression, but it is not a paper-faithful reproduction suite

### 7. Performance root cause: CAPA is dominated by exact shortest-path warming, not by the auction itself

Observed profiling on a 20-parcel / 20-local / 2x10-partner CAPA run:

- wall-clock: about `3.08s` under `cProfile`
- top cumulative path:
  - `env/chengdu.py:654 run_time_stepped_chengdu_batches`
  - `capa/batch_distance.py:112 precompute_for_insertions`
  - `capa/experiments.py:63 ChengduGraphTravelModel.distance`
  - `GraphUtils_ChengDu.py:560 getShortestDistance`

`run_dapa()` was negligible in that profile; the dominant cost was exact road-network distance warmup.

Relevant code:

- `env/chengdu.py:791-792` precomputes local insertion distances before `run_cama()`
- `env/chengdu.py:851-853` precomputes partner insertion distances before `run_dapa()`
- `capa/batch_distance.py:112-135` warms `(start,end)`, `(start,parcel)`, `(parcel,end)` for every courier route segment and every parcel

This means the current code pays exact shortest-path cost before most of the CAMA/DAPA feasibility filtering happens. That is why CAPA becomes slow quickly as:

- parcel count grows
- courier pool grows
- route lengths grow

The optimizations that do help are real:

- `PersistentDirectedDistanceCache` survives across batches
- `InsertionCache` survives across batches and invalidates on route mutation
- `LegacyCourierSnapshotCache` avoids repeated courier projection
- `GeoIndex` enables cheap lower-bound pruning

But these optimizations are not enough because the dominant cost is still the eager exact warmup itself.

## Runtime Judgment

For `5000` parcels, "CAPA is slow" is not purely a workflow illusion. The current exact Chengdu implementation is genuinely expensive.

However, the current slowness is not fully justified by paper-level algorithm complexity alone. The observed runtime is amplified by implementation and experiment-layer issues:

1. wrong `BPT` metric hides the true runtime
2. graph connectivity is nondeterministic because DFS starts from an arbitrary set element
3. exact batch warmup is performed too early and too broadly
4. split / point subprocess modes additionally repay graph-import cost per process

Therefore the correct answer is:

- slow is partly reasonable
- but the current experiment flow and supporting implementation are also wrong in ways that materially worsen or misreport CAPA runtime

## Recommended Fix Order

1. Fix graph loading determinism in `GraphUtils_ChengDu.py`
2. Redefine `BPT` to use real matching-round elapsed time instead of `decision_time_seconds`
3. Move batch-distance warmup behind cheap feasibility shortlisting, or warm only shortlisted couriers/parcels
4. Replace synthetic `alpha/beta/service_score/platform_qualities` with paper-consistent generation / history-derived values
5. Add full-route deadline feasibility instead of current pickup-only feasibility
6. Rebuild the paper experiment suite so RL-CAPA and paper datasets are not silently excluded
