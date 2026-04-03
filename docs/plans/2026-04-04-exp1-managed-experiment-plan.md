# Exp-1 Managed Experiment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a managed Chengdu `exp_1` runner that executes the paper-style `TR / CR / BPT vs |Γ|` experiment with `batch_size=30s`, supervises long-running rounds, retries CAPA with explicit parameter variants when it underperforms, and promotes the winning round result into the final result directory.

**Architecture:** Keep the existing `experiments/run_chengdu_exp1_num_parcels.py` paper-style sweep as the underlying execution primitive. Add a managed controller that runs one round at a time into `/tmp`, scores CAPA against the baselines from the same shared-environment summary, selects the next explicit CAPA parameter variant, and writes monitoring heartbeats plus round manifests while the job is running.

**Tech Stack:** Python 3, existing `experiments/` package, unified `algorithms/` registry, Chengdu shared environment, `unittest`, shell background process supervision.

---

### Task 1: Add CAPA runner parameter overrides

**Files:**
- Modify: `algorithms/capa_runner.py`
- Modify: `experiments/compare.py`
- Modify: `experiments/sweep.py`
- Test: `tests/test_experiments_seeding.py`

**Step 1: Write the failing test**

Extend the experiment runner-kwargs tests so a `fixed_config["extra"]` block can forward CAPA overrides such as `threshold_omega` and `utility_balance_gamma`.

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_experiments_seeding -v`

Expected: fail because CAPA runner kwargs ignore the extra overrides.

**Step 3: Write minimal implementation**

Update `CAPAAlgorithmRunner` to accept explicit `CAPAConfig` overrides and update the sweep/compare orchestration helpers to forward them when present in `ExperimentConfig.extra`.

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_experiments_seeding -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add algorithms/capa_runner.py experiments/compare.py experiments/sweep.py tests/test_experiments_seeding.py
git commit -m "feat(experiments): allow capa parameter overrides in sweeps"
```

### Task 2: Add managed Exp-1 controller

**Files:**
- Create: `experiments/run_exp1_managed.py`
- Modify: `experiments/paper_chengdu.py`
- Modify: `README.md`
- Test: `tests/test_paper_experiments.py`

**Step 1: Write the failing test**

Add tests that cover:
- round output written under `/tmp`-style paths
- CAPA parameter variants applied per round
- score-based success / retry decision
- final manifest written with the winning round summary

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_paper_experiments -v`

Expected: fail because the managed controller does not exist.

**Step 3: Write minimal implementation**

Create a managed controller that:
- runs `exp_1` one round at a time
- uses explicit CAPA parameter variants, not hidden heuristics
- evaluates CAPA against baselines from the same summary
- stores each round in `/tmp/...`
- writes `status.json`, `round_manifest.json`, and `analysis.json`
- promotes the winning round to the final result directory once CAPA is good enough

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_paper_experiments -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add experiments/run_exp1_managed.py experiments/paper_chengdu.py README.md tests/test_paper_experiments.py
git commit -m "feat(experiments): add managed exp1 controller"
```

### Task 3: Add monitoring and execution helpers

**Files:**
- Modify: `experiments/run_exp1_managed.py`
- Optionally create: `experiments/monitoring.py`
- Test: `tests/test_paper_experiments.py`

**Step 1: Write the failing test**

Add tests that the controller emits heartbeat / monitoring files containing:
- current round
- active PID when launched through the CLI wrapper
- elapsed time
- latest completed parcel-count point if available

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_paper_experiments -v`

Expected: fail because monitoring artifacts are missing.

**Step 3: Write minimal implementation**

Emit periodic status updates from the controller and add a shell launch recipe that runs:
- the managed controller in the background
- a periodic monitor loop writing process snapshots into `/tmp`

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_paper_experiments -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add experiments/run_exp1_managed.py tests/test_paper_experiments.py
git commit -m "feat(experiments): add exp1 monitoring artifacts"
```

### Task 4: Verify the full implementation

**Files:**
- Verify only

**Step 1: Run focused tests**

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

**Step 3: Commit any final doc/test adjustments**

```bash
git add -A
git commit -m "test(experiments): verify managed exp1 workflow"
```

### Task 5: Launch Exp-1 and supervise it

**Files:**
- Runtime only

**Step 1: Start the managed experiment**

Run the managed controller with:
- `batch_size=30`
- the default formal `exp_1` parcel-count grid
- algorithms `capa greedy ramcom mra basegta impgta`
- `/tmp` round outputs

**Step 2: Start background monitoring**

Launch a periodic monitor loop that records:
- PID state
- CPU / elapsed time
- round status file contents
- newest summary files under the round directory

**Step 3: Review each completed round**

If CAPA is far worse than baselines:
- inspect `TR`, `CR`, and `BPT` deltas
- select the next explicit CAPA variant from the managed controller plan
- continue to the next round

If CAPA is competitive:
- promote the winning round directory into the final result directory
- persist the final manifest

**Step 4: Commit docs/scripts if runtime adjustments were necessary**

```bash
git add -A
git commit -m "experiment(exp1): run managed parcel-count experiment"
```
