# Batch-End Matching and Route Deadline Feasibility Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development while implementing each behavior and superpowers:verification-before-completion before reporting completion.

**Goal:** Align GTA and MRA decision times with CAPA batch-end execution and reject any route insertion that makes the new parcel or affected downstream route stops late.

**Architecture:** Preserve each algorithm's selection/payment logic and repair only decision timing and shared feasibility semantics. CAPA-backed algorithms gain deadline-carrying courier snapshots plus an exact feasible insertion selector; GTA's independent legacy route selector receives an equivalent route replay check.

**Tech Stack:** Python 3, dataclasses, existing Chengdu environment adapters, `pytest`.

---

### Task 1: Lock Downstream Route Deadline Semantics

**Files:**
- Modify: `tests/test_capa_local.py`
- Modify: `tests/test_capa_auction.py`
- Modify: `tests/test_metric_alignment.py`

**Step 1: Write failing tests**

Add tests with route `start -> existing -> depot` where inserting `new` before
`existing` is distance-preferred and reaches `new` in time, but causes
`existing` to miss its deadline:

```python
courier = Courier(
    courier_id="c1",
    current_location="start",
    depot_location="depot",
    capacity=10.0,
    route_locations=["existing"],
    route_deadlines=[5],
)
new = Parcel("new", "new", 0, 10, 1.0, 10.0)
assert not is_feasible_local_match(new, courier, travel_model, now=0)
```

Cover CAMA local rejection, DAPA cross rejection, a shared legacy insertion
used by MRA/RamCOM, and `find_best_legacy_insertion_option()` used by GTA.

**Step 2: Run tests to verify RED**

Run:
```bash
python3 -m pytest -q tests/test_capa_local.py tests/test_capa_auction.py tests/test_metric_alignment.py
```

Expected: new downstream-deadline tests fail because current feasibility only
checks the inserted parcel.

### Task 2: Implement Shared Feasible Insertion Validation

**Files:**
- Modify: `capa/models.py`
- Modify: `capa/utility.py`
- Modify: `capa/cama.py`
- Modify: `capa/dapa.py`
- Modify: `env/chengdu.py`
- Modify: `baselines/common.py`
- Modify: `baselines/greedy.py`
- Modify: `baselines/mra.py`
- Modify: `rl_capa/env.py`

**Step 1: Extend route state minimally**

Add `route_deadlines: List[float | None]` to `Courier`, fill it while
projecting legacy `re_schedule`, include it in route signatures, and update it
when CAPA applies a new assignment.

**Step 2: Add exact feasible insertion selection**

Add a utility function with this contract:

```python
def find_best_deadline_feasible_insertion(
    parcel: Parcel,
    courier: Courier,
    travel_model: DistanceMatrixTravelModel,
    now: int,
    ...
) -> tuple[float, int] | None:
    """Select the minimum-detour insertion whose known route deadlines remain feasible."""
```

For each insertion index, traverse the new route from `courier.current_location`
at `now`, rejecting the index if the new parcel or any known downstream
deadline is missed. Select the feasible index with highest Eq.6 detour ratio.

**Step 3: Route all committing selection paths through it**

Use the feasible selector for CAMA/DAPA matching and for insertion-index
selection in the Chengdu, Greedy, MRA, and RL direct-local paths. Preserve the
cheap shortlist filters as optimistic prefilters only.

**Step 4: Run tests to verify GREEN**

Run:
```bash
python3 -m pytest -q tests/test_capa_local.py tests/test_capa_auction.py tests/test_metric_alignment.py tests/test_rl_env_smoke.py
```

Expected: downstream-deadline tests and affected existing tests pass.

### Task 3: Implement GTA Legacy Route Validation and Batch-End Timing

**Files:**
- Modify: `baselines/gta.py`
- Modify: `algorithms/basegta_runner.py`
- Modify: `algorithms/impgta_runner.py`
- Modify: `runner.py`
- Modify: `experiments/sweep.py`
- Modify: `experiments/compare.py`
- Modify: `experiments/framework/point_runner.py`
- Modify: `experiments/paper_chengdu.py`
- Modify: `tests/test_metric_alignment.py`

**Step 1: Write failing timing tests**

Inject a selector or movement callback that records `now`; for tasks arriving
inside `[batch_start, batch_end)`, assert BaseGTA and ImpGTA evaluate at
`batch_end`, not their arrival times. Add a runner-kwargs test proving
`batch_size` reaches both GTA variants.

**Step 2: Run tests to verify RED**

Run:
```bash
python3 -m pytest -q tests/test_metric_alignment.py
```

Expected: new GTA batch timing/interface tests fail under arrival-time
processing.

**Step 3: Implement batch-end GTA epochs**

Add `batch_size` to both public GTA runners and their wrappers. Accumulate
tasks by batch, advance active routes to the batch boundary, then run the
existing BaseGTA or ImpGTA decision rules over that batch at `now=batch_end`.
Pass the configured batch size through CLI/sweep/comparison entrypoints.

**Step 4: Add legacy route replay**

Within `find_best_legacy_insertion_option()`, accept an insertion only when
traversing the candidate legacy schedule at `now` keeps the inserted task and
every later task within its model-facing deadline.

**Step 5: Run tests to verify GREEN**

Run:
```bash
python3 -m pytest -q tests/test_metric_alignment.py
```

Expected: GTA timing, revenue, AIM and route-feasibility tests pass.

### Task 4: Align MRA Decision Epoch to Batch End

**Files:**
- Modify: `baselines/mra.py`
- Modify: `tests/test_mra_bpt.py`
- Modify: `tests/test_metric_alignment.py`

**Step 1: Write failing MRA timing test**

Record the `now` passed to `build_legacy_feasible_insertions()` for a
`batch_size=30` bucket starting at `0`; require `30`.

**Step 2: Run test to verify RED**

Run:
```bash
python3 -m pytest -q tests/test_mra_bpt.py tests/test_metric_alignment.py
```

Expected: the new assertion observes `0` before implementation.

**Step 3: Implement movement-before-matching**

For each MRA bucket, advance already assigned routes through the batch window,
set `now` to the resulting batch end, and then execute the unchanged multi-round
graph construction/assignment loop.

**Step 4: Run test to verify GREEN**

Run:
```bash
python3 -m pytest -q tests/test_mra_bpt.py tests/test_metric_alignment.py
```

Expected: MRA batch timing and BPT tests pass.

### Task 5: Verification Checkpoints

**Files:**
- Verify: all changed files and regression suites

**Step 1: Focused behavior suite**

Run:
```bash
python3 -m pytest -q tests/test_capa_local.py tests/test_capa_auction.py tests/test_metric_alignment.py tests/test_mra_bpt.py tests/test_deadline_delivery_accounting.py tests/test_rl_env_smoke.py
```

**Step 2: Compile modified modules**

Run:
```bash
python3 -m py_compile capa/models.py capa/utility.py capa/cama.py capa/dapa.py env/chengdu.py baselines/common.py baselines/greedy.py baselines/gta.py baselines/mra.py rl_capa/env.py algorithms/basegta_runner.py algorithms/impgta_runner.py runner.py
```

**Step 3: Full regression suite**

Run:
```bash
python3 -m pytest -q tests
```

**Step 4: Review diff and commit verified checkpoints**

Commit documentation, tests, and implementation only after the associated
verification commands succeed.
