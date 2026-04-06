# Canonical Seed For Exp2-Exp6 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make Chengdu paper experiments `Exp-2`, `Exp-3`, `Exp-4`, and `Exp-6` use canonical environment seeds so that point-to-point comparisons keep the same underlying parcels, stations, road graph, and baseline courier population while only changing the intended sweep axis.

**Architecture:** Reuse the existing seeded experiment framework already used by `Exp-1`, but generalize canonical seed construction and environment derivation per axis. The key change is to build one sufficiently large canonical environment for each sweep and then derive point environments deterministically from that seed instead of rebuilding each point independently.

**Tech Stack:** Python, existing Chengdu environment builder, experiment seeding utilities, paper experiment wrappers.

---

### Task 1: Define per-axis canonical-seed policy

**Files:**
- Modify: `experiments/paper_chengdu.py`
- Modify: `experiments/seeding.py`

**Step 1: Write down the canonical-build rule for each axis**

- `num_parcels`
  - canonical build uses max `|Γ|`
  - derive by truncating the ordered task list prefix
- `local_couriers`
  - canonical build uses max `|C|`
  - same parcels, same partner pools
  - derive by taking a deterministic prefix of the canonical local-courier pool
- `service_radius`
  - canonical build uses fixed default environment
  - derive by only changing `service_radius_km`
- `platforms`
  - canonical build uses max `|P|`
  - derive by taking the first `k` partner platforms from the canonical partner mapping
- `courier_capacity`
  - canonical build uses the minimum capacity in the preset, so canonical initial routes remain feasible for every larger capacity point
  - derive by increasing capacity only, not regenerating courier history

**Step 2: Reject non-rigorous alternatives**

Do not rebuild each point independently once the canonical-seed path exists.  
Do not use fallback or random resampling inside derive logic.

**Step 3: Commit**

```bash
git add docs/plans/2026-04-06-canonical-seed-exp2-exp6.md
git commit -m "docs(plan): add canonical seed plan for exp2-exp6"
```

### Task 2: Add failing tests for per-axis derivation

**Files:**
- Create locally: `tests/test_paper_canonical_seed_axes.py`

**Step 1: Write a failing test for `local_couriers`**

Test expectation:
- build one canonical environment with a larger local-courier pool
- derive two environments for `|C|=small` and `|C|=large`
- tasks must match
- partner platform pools must match
- small local pool must equal the prefix of the large canonical local pool

**Step 2: Write a failing test for `platforms`**

Test expectation:
- tasks and local couriers stay unchanged
- partner platform ids are truncated deterministically to the requested count

**Step 3: Write a failing test for `service_radius`**

Test expectation:
- tasks and courier populations stay unchanged
- only `service_radius_km` changes

**Step 4: Write a failing test for `courier_capacity`**

Test expectation:
- tasks and courier identities stay unchanged
- only capacity fields change
- canonical build uses the minimum configured capacity for the axis

**Step 5: Run the tests and confirm they fail for the right reason**

Run:

```bash
python3 -m unittest tests.test_paper_canonical_seed_axes -v
```

Expected:
- FAIL because the derive helpers do not yet exist or do not preserve these invariants.

### Task 3: Implement deterministic derive helpers

**Files:**
- Modify: `experiments/seeding.py`

**Step 1: Add explicit derive helpers**

Add:
- `derive_environment_with_local_couriers_from_seed(...)`
- `derive_environment_with_platforms_from_seed(...)`
- `derive_environment_with_service_radius_from_seed(...)`
- `derive_environment_with_courier_capacity_from_seed(...)`

Each helper must:
- clone the canonical seed
- mutate only the intended axis
- preserve all other initialization state

**Step 2: Add courier-capacity mutation helpers**

If needed, update cloned legacy courier objects so that:
- `max_weight`
- any mirrored capacity fields used by algorithms
reflect the derived capacity point

Do not regenerate routes. The point of this axis derivation is to keep the courier history fixed.

**Step 3: Add one axis-dispatch helper**

Add one dispatcher:
- `derive_environment_for_axis(seed, axis, value)`

This becomes the single source of truth used by point and split experiment flows.

### Task 4: Embed canonical seed build into paper point/split flows

**Files:**
- Modify: `experiments/paper_chengdu.py`

**Step 1: Build canonical seeds for every split axis**

Replace the current `if axis == "num_parcels"` special-case with a generic per-axis canonical-seed builder.

The builder must choose canonical config using the preset values:
- max for `num_parcels`
- max for `local_couriers`
- max for `platforms`
- fixed config for `service_radius`
- min for `courier_capacity`

**Step 2: Use canonical seeds in point mode whenever `--seed-path` is supplied**

Point mode should not special-case `num_parcels` anymore.

**Step 3: Use the same derive dispatcher in split and point**

All point subprocesses must resolve through the same `derive_environment_for_axis(...)` path.

### Task 5: Verify rigor and smoke-test the new flow

**Files:**
- No committed file changes required

**Step 1: Run the local derivation tests**

Run:

```bash
python3 -m unittest tests.test_paper_canonical_seed_axes -v
```

Expected:
- PASS

**Step 2: Run Exp-2 split smoke with canonical seed**

Run:

```bash
python3 experiments/run_chengdu_exp2_couriers.py \
  --execution-mode split \
  --tmp-root /tmp/chengdu_exp2_canonical_smoke \
  --output-dir /tmp/chengdu_exp2_canonical_smoke_out \
  --preset smoke \
  --algorithms capa greedy \
  --data-dir Data \
  --num-parcels 20 \
  --platforms 1 \
  --couriers-per-platform 1 \
  --courier-capacity 50 \
  --service-radius-km 1.0 \
  --batch-size 30 \
  --poll-seconds 1
```

Expected:
- `canonical_seed.pkl` exists under `tmp_root`
- point directories show progress and finish
- aggregate summary is produced

**Step 3: Run one smoke for a non-courier axis**

Run:

```bash
python3 experiments/run_chengdu_exp4_platforms.py \
  --execution-mode split \
  --tmp-root /tmp/chengdu_exp4_canonical_smoke \
  --output-dir /tmp/chengdu_exp4_canonical_smoke_out \
  --preset smoke \
  --algorithms capa greedy \
  --data-dir Data \
  --num-parcels 20 \
  --local-couriers 8 \
  --couriers-per-platform 1 \
  --courier-capacity 50 \
  --service-radius-km 1.0 \
  --batch-size 30 \
  --poll-seconds 1
```

Expected:
- `canonical_seed.pkl` exists
- output summary exists

### Task 6: Commit the implementation

**Step 1: Commit the finished feature**

```bash
git add experiments/seeding.py experiments/paper_chengdu.py docs/plans/2026-04-06-canonical-seed-exp2-exp6.md
git commit -m "feat(experiments): add canonical seed derivation for exp2-exp6"
```
