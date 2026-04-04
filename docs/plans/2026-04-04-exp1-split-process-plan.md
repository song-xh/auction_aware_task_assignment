# Exp-1 Split-Process Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the monolithic managed `exp_1` controller with a split-process launcher that runs `|Γ| = 1000 / 2000 / 3000 / 5000` as four independent experiment processes while preserving one shared canonical Chengdu initialization for stations and couriers.

**Architecture:** Build one canonical Chengdu environment at the maximum parcel count, persist a reusable seed bundle, then launch one point-runner process per parcel-count value. Each point runner reconstructs its environment from the same persisted station/courier seed and truncates the parcel list deterministically. A launcher monitors all point processes and writes an aggregate summary/plots once all four point results exist.

**Tech Stack:** Python 3, existing `experiments/` package, `pickle`, unified algorithm runners, Chengdu shared environment, `unittest`, shell process supervision.

---

### Task 1: Add persisted canonical Chengdu seed support

**Files:**
- Modify: `experiments/seeding.py`
- Test: `tests/test_experiments_seeding.py`

**Step 1: Write the failing test**

Add tests that:
- persist a Chengdu environment seed bundle to disk
- reload it
- rebuild two environments with different `num_parcels` values from the same bundle
- verify the courier/station initialization matches while the task list is a deterministic prefix

**Step 2: Run test to verify it fails**

Run:

```bash
python3 -m unittest tests.test_experiments_seeding -v
```

Expected: fail because persisted canonical seeds do not exist yet.

**Step 3: Write minimal implementation**

Add helpers to:
- build a canonical environment seed at max parcel count
- persist serializable environment state
- reload it
- derive point-specific environments by slicing the task stream deterministically

**Step 4: Run test to verify it passes**

Run:

```bash
python3 -m unittest tests.test_experiments_seeding -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add experiments/seeding.py tests/test_experiments_seeding.py
git commit -m "feat(experiments): persist canonical Chengdu seeds for split runs"
```

### Task 2: Add point runner and split launcher

**Files:**
- Create: `experiments/run_exp1_point.py`
- Create: `experiments/run_exp1_split.py`
- Modify: `README.md`
- Test: `tests/test_paper_experiments.py`

**Step 1: Write the failing test**

Add tests that:
- run one point from a persisted seed bundle
- write per-point `summary.json`
- launch a split suite with four parcel-count points
- aggregate only after every point result exists

**Step 2: Run test to verify it fails**

Run:

```bash
python3 -m unittest tests.test_paper_experiments -v
```

Expected: fail because the split launcher and point runner do not exist.

**Step 3: Write minimal implementation**

Create:
- `run_exp1_point.py` to run one `num_parcels` point from a shared seed bundle
- `run_exp1_split.py` to:
  - build/persist the canonical seed once
  - launch 4 point processes
  - track PIDs and statuses
  - aggregate the point summaries and plots

**Step 4: Run test to verify it passes**

Run:

```bash
python3 -m unittest tests.test_paper_experiments -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add experiments/run_exp1_point.py experiments/run_exp1_split.py README.md tests/test_paper_experiments.py
git commit -m "feat(experiments): add split-process exp1 launcher"
```

### Task 3: Verify and launch the split experiment

**Files:**
- Runtime only

**Step 1: Run focused verification**

Run:

```bash
python3 -m unittest tests.test_experiments_seeding tests.test_paper_experiments tests.test_runner_cli -v
```

Expected: PASS.

**Step 2: Run full test suite**

Run:

```bash
python3 -m unittest discover -s tests -v
```

Expected: PASS.

**Step 3: Launch the four-point Exp-1 suite**

Run the split launcher with:
- `batch_size=30`
- formal parcel-count values
- one canonical shared seed
- four independent point processes

**Step 4: Monitor**

Monitor:
- launcher PID
- point PIDs
- per-point summary files
- aggregate status file

**Step 5: Commit any runtime-only script fixes if required**

```bash
git add -A
git commit -m "experiment(exp1): launch split-process parcel-count suite"
```
