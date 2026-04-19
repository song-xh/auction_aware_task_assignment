# 2026-04-07 Update Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the two runtime-critical CAPA problems identified on the current unified path: nondeterministic Chengdu graph loading and over-eager exact distance warmup before feasibility filtering.

**Architecture:** Keep the active runtime path unchanged at the top level, i.e. `algorithms/capa_runner.py -> env/chengdu.py -> capa/cama.py + capa/dapa.py`, but repair the two root-cause layers beneath it. First, make the Chengdu graph import deterministic by selecting the largest connected component rather than starting DFS from an arbitrary `set` element. Second, change local/cross exact distance warmup from a full Cartesian product over all couriers and parcels to a shortlist-driven warmup over only plausibly feasible courier-parcel pairs.

**Tech Stack:** Python, legacy Chengdu graph loader, unified CAPA environment, `unittest`, profiling via `cProfile`.

---

## Scope And Metric Contract

This plan is only for:

1. graph-loading determinism and correctness
2. distance-warmup placement and scope

This plan is **not** changing the top-level experiment definition or the current CAPA formula implementation.

`BPT` is treated here as a **matching-only algorithm cost**, not full batch wall-clock time. That means:

- keep simulator movement, plotting, and environment build outside `BPT`
- but treat shortest-path lookup and insertion evaluation as part of matching cost, because they are intrinsic to CAPA matching

Any future `BPT` cleanup must preserve that contract.

## Root-Cause Analysis

### Problem A: Chengdu graph loading is nondeterministic

Active code path:

- `Tasks_ChengDu.py` imports `GraphUtils_ChengDu`
- `GraphUtils_ChengDu.py` builds global `g` and `s` at import time
- `env/chengdu.py` calls `build_framework_chengdu_environment()`
- `build_framework_chengdu_environment()` uses `Framework_ChengDu` / `Tasks_ChengDu`, which depend on that global graph
- split / point / managed experiment modes start fresh Python processes, so each subprocess reparses the graph

Current logic:

- `GraphUtils_ChengDu.py:230` builds the candidate node pool in `nSet = set()`
- `GraphUtils_ChengDu.py:333` converts it to `nList = list(nSet)`
- `GraphUtils_ChengDu.py:335` runs `DFSSearch(..., nList[0], ...)`

Why this is wrong:

- `set` iteration order is not stable across fresh Python processes
- so `nList[0]` is not deterministic
- DFS therefore starts from an arbitrary connected component, not the main road-network component

Observed effect:

- repeated fresh imports of the same graph produced both:
  - `After DFS nodeNumber: 36630 | edgeNumber: 50786`
  - `After DFS nodeNumber: 1 | edgeNumber: 1`
- when a tiny component is selected, shortest-path lookup frequently falls through to:
  - `GraphUtils_ChengDu.py:607` -> `print("no paths suitable.")`

How this amplifies CAPA runtime:

1. tasks, stations, and couriers are mapped against a damaged graph context
2. many shortest-path queries become failed searches rather than quick hits
3. each failed search still expands the frontier before concluding unreachable
4. CAPA calls shortest-path lookup in:
   - legacy courier seeding
   - movement simulation
   - batch distance warmup
   - insertion search
5. split/process-based experiments multiply the problem because each subprocess reimports the graph independently

This is therefore both a **correctness bug** and a **runtime amplifier**.

### Problem B: exact distance warmup happens before feasibility filtering

Active code path:

- `env/chengdu.py:791-792`
  - `bdm = BatchDistanceMatrix(timed_travel_model)`
  - `bdm.precompute_for_insertions(local_snapshots, batch_parcels)`
- only afterwards:
  - `env/chengdu.py:793` calls `run_cama()`
  - `capa/cama.py:111-117` starts filtering couriers by availability, load, deadline lower bound, radius, and exact arrival time

The same pattern repeats for cross-platform matching:

- `env/chengdu.py:851-853`
  - build `partner_snapshots`
  - `bdm.precompute_for_insertions(partner_snapshots, remaining_parcels)`
- only afterwards:
  - `env/chengdu.py:854` calls `run_dapa()`
  - `capa/dapa.py:171-179` starts filtering partner couriers by feasibility

Current warmup logic:

- `capa/batch_distance.py:112-135`
- for each courier
- for each route segment
- for each parcel
- warm:
  - `start -> end`
  - `start -> parcel`
  - `parcel -> end`

Why this is wrong:

- exact shortest-path work is being paid **before** most couriers are ruled out
- so CAPA warms exact distances for many pairs that later fail on:
  - availability
  - capacity
  - deadline lower bound
  - service radius lower bound
  - exact arrival-time check

Observed load pattern:

- on the Chengdu `1000`-parcel slice with `batch_seconds = 300`, all `1000` parcels fall into the first arrival window
- with a `200 local + 200 partner` courier seed, the initial average route segment counts observed were about:
  - local: `36.9`
  - partner: `38.9`

This yields an approximate first-round warmup worklist upper bound of:

- local: `200 * 36.9 * 1000 * 3 ≈ 22.1M`
- partner: `200 * 38.9 * 1000 * 3 ≈ 23.3M`

before feasibility filtering, before deduplication, and before CAMA/DAPA has decided that most of those pairs are useless.

Profiling evidence:

- small `cProfile` run showed the dominant cumulative cost in:
  - `env/chengdu.py:654 run_time_stepped_chengdu_batches`
  - `capa/batch_distance.py:112 precompute_for_insertions`
  - `capa/experiments.py:63 ChengduGraphTravelModel.distance`
  - `GraphUtils_ChengDu.py:560 getShortestDistance`
- `run_dapa()` itself was not the hot path

So the current slowdown is not mainly “auction logic is heavy”; it is “exact route-network warming is paid too early and too broadly”.

## Recommended Repair Strategy

### Graph loading

Recommended approach: **select the largest connected component deterministically**, not a deterministic single root and not “first set element”.

Why:

- choosing `min(node_id)` would be deterministic but could still pick a tiny component
- keeping all components would preserve islands but keeps useless road fragments in the main runtime graph
- selecting the largest connected component matches the intended road-network use and removes nondeterminism

### Distance warmup

Recommended approach: **shortlist first, warm second**.

Why:

- pure lazy evaluation removes locality benefits and can thrash the graph repeatedly
- the current eager Cartesian warmup is too broad
- the best compromise is:
  - cheap filter over `(parcel, courier)` pairs first
  - exact warmup only for shortlisted pairs
  - reuse the shortlisted pairs inside `run_cama()` / `run_dapa()` rather than rescanning the full courier pool

## Implementation Plan

### Task 1: Lock graph nondeterminism into a reproducible test

**Files:**
- Create: `tests/test_graph_utils_chengdu.py`
- Create: `tests/__init__.py`

**Step 1: Write the failing reproduction test**

Add a subprocess-based test that:

- starts multiple fresh Python interpreters
- imports `GraphUtils_ChengDu`
- captures the printed `After DFS nodeNumber` / `edgeNumber`
- asserts:
  - all runs return the same node/edge counts
  - the retained component is above a sanity floor such as `> 10000` nodes

**Step 2: Run the focused test to verify it fails**

Run:

```bash
python -m unittest tests.test_graph_utils_chengdu -v
```

Expected:

- flaky or hard failure on the current loader because the DFS root is arbitrary

**Step 3: Review points**

- the test must use fresh subprocesses, not repeated imports in one process
- the assertion must check both determinism and non-trivial retained graph size

### Task 2: Replace arbitrary DFS-root selection with deterministic largest-component selection

**Files:**
- Modify: `GraphUtils_ChengDu.py`
- Modify: `docs/implementation_notes.md`

**Step 1: Refactor component selection**

Replace the current:

- `nList = list(nSet)`
- `DFSSearch(..., nList[0], ...)`

with:

1. a component enumeration helper over `nMap` / `eMap`
2. deterministic selection of the largest connected component
3. deterministic tie-breaker using the smallest node id
4. population of `context.nMap`, `context.eMap`, `context.nList`, `context.eList` from that chosen component only

**Step 2: Preserve diagnostic logging**

Add explicit logs for:

- total connected components found
- selected component node/edge counts
- selected root id used for traversal

**Step 3: Run focused verification**

Run:

```bash
python -m unittest tests.test_graph_utils_chengdu -v
python - <<'PY'
for _ in range(5):
    import subprocess, sys
    out = subprocess.check_output([sys.executable, "-c", "import GraphUtils_ChengDu"], text=True)
    print(out.splitlines()[-2:])
PY
```

Expected:

- every fresh process reports the same retained graph size
- no runs collapse to `1` or `2` nodes

**Step 4: Review points**

- the fix must not depend on Python hash randomization behavior
- the selected component must be the main road-network component, not merely deterministic
- `findNode()` and shortest-path lookup must still operate on the chosen component without API changes

### Task 3: Add a first-pass cheap shortlist for local matching

**Files:**
- Modify: `capa/cama.py`
- Modify: `capa/constraints.py`
- Modify: `env/chengdu.py`

**Step 1: Split local matching into two phases**

Introduce a first pass that builds parcel-local-courier candidate subsets using only cheap checks:

- availability
- load / capacity
- geo deadline lower bound
- geo service-radius lower bound

This first pass must not call route-segment insertion search.

**Step 2: Carry the shortlist forward**

Expose the shortlisted local candidate map to the environment layer so the exact warmup is driven by the shortlist rather than the full Cartesian product.

**Step 3: Run a local correctness smoke test**

Create or extend a local matching test to assert that:

- obviously infeasible couriers are excluded before warmup
- feasible assignments on a deterministic toy fixture are unchanged

Run:

```bash
python -m unittest tests.test_capa_local -v
```

Expected:

- same accepted local assignments on the toy fixture
- reduced exact-pair preparation count

**Step 4: Review points**

- no route insertion should happen in the shortlist phase
- the shortlist must be a subset, not a ranking heuristic that changes paper semantics
- exact arrival-time feasibility may remain in the second pass, but obvious losers must not reach warmup

### Task 4: Change batch distance warmup from full Cartesian product to shortlist-driven pairs

**Files:**
- Modify: `capa/batch_distance.py`
- Modify: `env/chengdu.py`
- Modify: `tests/test_capa_warmup.py`

**Step 1: Add explicit pair-scoped warmup**

Refactor `BatchDistanceMatrix.precompute_for_insertions()` so it can warm exact distances for:

- explicit `(courier, parcel)` feasible pairs
- not `all couriers x all parcels`

Suggested API shape:

- accept a sequence of `(courier, parcel)` pairs or `courier -> parcels` mapping
- only warm route segments for those couriers against those parcels

**Step 2: Wire local warmup to the shortlist**

In `env/chengdu.py`, replace:

```python
bdm.precompute_for_insertions(local_snapshots, batch_parcels)
```

with shortlist-driven warmup over only the locally plausible pairs.

**Step 3: Add a call-count regression test**

The test should compare old and new warmup shapes on a deterministic fake travel model and assert that:

- the number of exact `distance()` calls drops materially
- accepted local assignments remain unchanged

**Step 4: Run focused verification**

Run:

```bash
python -m unittest tests.test_capa_warmup tests.test_capa_local -v
```

Expected:

- lower exact-distance call count
- unchanged local assignment result on deterministic fixtures

**Step 5: Review points**

- warmup must be driven by shortlist data, not rebuilt from full courier/parcels later
- cache keys and persistent cache semantics must stay valid
- no accidental symmetric-distance assumptions may be reintroduced

### Task 5: Apply the same shortlist-then-warm structure to DAPA

**Files:**
- Modify: `capa/dapa.py`
- Modify: `env/chengdu.py`
- Modify: `tests/test_capa_auction.py`
- Modify: `tests/test_capa_warmup.py`

**Step 1: Add partner-side cheap shortlist**

Before exact partner warmup, build per-platform candidate courier subsets using:

- availability
- load / capacity
- geo deadline lower bound
- geo service-radius lower bound

**Step 2: Warm only shortlisted cross pairs**

Replace:

```python
bdm.precompute_for_insertions(partner_snapshots, remaining_parcels)
```

with shortlist-driven exact warmup over only partner couriers that survive the first-pass filter.

**Step 3: Reuse shortlist data inside `run_dapa()`**

Avoid rescanning every partner courier after warmup; the shortlisted set should feed the FPSA stage directly.

**Step 4: Run focused verification**

Run:

```bash
python -m unittest tests.test_capa_auction tests.test_capa_warmup -v
```

Expected:

- same auction winners / payments on deterministic toy fixtures
- reduced exact-distance warmup count

**Step 5: Review points**

- keep Eq.1-Eq.4 logic unchanged while changing only the candidate preparation path
- ensure single-platform and multi-platform payment branches still behave identically on fixtures
- do not let shortlist logic silently remove truly feasible couriers

### Task 6: Add instrumentation to prove the fix actually attacks the hotspot

**Files:**
- Modify: `env/chengdu.py`
- Modify: `capa/timing.py`
- Modify: `docs/implementation_notes.md`

**Step 1: Add per-batch diagnostics**

Record for each batch:

- local shortlist pair count
- local exact warmup pair count
- partner shortlist pair count
- partner exact warmup pair count
- distance-cache entry growth

**Step 2: Run a before/after benchmark**

Use one deterministic point, e.g.:

- `num_parcels = 1000`
- `local_couriers = 200`
- `platforms = 4`
- `couriers_per_platform = 50`
- `batch_size = 300`

Capture:

- wall-clock runtime
- matching-only `BPT`
- exact distance call counts
- local / partner warmup pair counts

**Step 3: Review points**

- the benchmark must be run on the same deterministic graph component after Task 2
- compare like-for-like environment seeds
- success is measured by reduced exact distance work, not by changing algorithm semantics

### Task 7: Final review checkpoint before implementation closes

**Files:**
- Modify: `docs/update_0407.md`
- Modify: `docs/2026-04-07-capa-paper-audit.md`

**Step 1: Final code review checklist**

Confirm all of the following:

1. repeated fresh graph imports retain the same main component every time
2. local warmup no longer runs over `local_snapshots x batch_parcels`
3. partner warmup no longer runs over `partner_snapshots x remaining_parcels`
4. local/cross assignment outputs on deterministic fixtures are unchanged
5. `BPT` still represents matching-only cost and still excludes simulator movement / plotting / environment build

**Step 2: Verification commands**

Run:

```bash
python -m unittest discover -s tests -v
python -m experiments.run_chengdu_exp1_num_parcels --execution-mode point --point-value 1000 --algorithms capa --output-dir /tmp/exp1_point_check
```

Expected:

- test suite passes
- CAPA point run finishes with deterministic graph logs and materially reduced exact warmup work

## Suggested Commit Order

1. `test: reproduce graph nondeterminism across fresh imports`
2. `fix(graph): select largest connected component deterministically`
3. `test: lock shortlist-driven warmup call counts`
4. `refactor(cama): split cheap feasibility shortlist from exact evaluation`
5. `refactor(dapa): narrow exact warmup to shortlisted cross pairs`
6. `perf(env): add batch warmup diagnostics and benchmark notes`
