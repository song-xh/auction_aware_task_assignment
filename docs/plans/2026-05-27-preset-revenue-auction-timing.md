# Preset Revenue And Auction Timing Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add preset-specific Exp-1 defaults, delivered TR decomposition, and CAPA-only DAPA timing metrics `AT_full` and `AT_single`.

**Architecture:** Centralize preset background overrides in the paper experiment configuration layer and resolve them before a point is generated. Extend CAPA batch timing with DAPA-only counters, aggregate those counters through existing run metrics, and compute local/cross revenue from delivered outcomes for CAPA, RL-CAPA, and baselines without changing `TR`, `CR`, or `BPT` semantics.

**Tech Stack:** Python dataclasses, argparse experiment entrypoints, pytest/unittest, existing CAPA/Chengdu runtime.

---

### Task 1: Resolve Preset Background Defaults

**Files:**
- Modify: `experiments/paper_config.py`
- Modify: `experiments/paper_chengdu.py`
- Modify: `tests/test_paper_experiment_presets.py`

**Step 1: Write failing tests**

Add tests that parse paper experiment arguments and assert:

```python
formal = build_fixed_config_from_args(build_script_parser("x").parse_args(["--output-dir", "/tmp/x", "--preset", "formal"]))
ny = build_fixed_config_from_args(build_script_parser("x").parse_args(["--output-dir", "/tmp/x", "--preset", "ny"]))
assert formal["local_couriers"] == 3000
assert formal["couriers_per_platform"] == 500
assert formal["deadline_seconds"] == 720
assert ny["local_couriers"] == 300
assert ny["couriers_per_platform"] == 50
assert ny["deadline_seconds"] == 720
assert PAPER_SUITE_PRESETS["chengdu-paper"]["ny"]["num_parcels"] == [500, 2000, 5000, 10000, 20000]
```

Add an override test asserting explicitly provided `--local-couriers`,
`--couriers-per-platform`, and `--deadline-seconds` win.

**Step 2: Verify tests fail**

Run:

```bash
python3 -m pytest -q tests/test_paper_experiment_presets.py
```

Expected: failures for missing `ny` fixed defaults and missing default
`deadline_seconds=720`.

**Step 3: Implement minimal configuration resolution**

Add a centralized preset-fixed-default mapping and helper. Change parser
defaults for preset-controlled optional values to `None`, then resolve them
from `args.preset` in `build_fixed_config_from_args()`. Use the same helper in
programmatic paper sweep entrypoints before merging explicit overrides.

**Step 4: Verify tests pass**

Run the Task 1 pytest command and confirm it passes.

**Step 5: Commit**

```bash
git add experiments/paper_config.py experiments/paper_chengdu.py tests/test_paper_experiment_presets.py
git commit -m "config(experiments): add formal and ny fixed defaults"
```

### Task 2: Add CAPA Revenue Split And DAPA Timing Aggregation

**Files:**
- Modify: `capa/models.py`
- Modify: `capa/utility.py`
- Modify: `capa/dapa.py`
- Modify: `capa/metrics.py`
- Modify: `algorithms/capa_runner.py`
- Modify: `tests/test_metric_alignment.py`
- Modify: `tests/test_algorithm_summary_fields.py`

**Step 1: Write failing tests**

Add metric tests constructing delivered local and cross assignments plus batch
timing:

```python
timing = BatchTimingBreakdown(
    auction_full_time_seconds=0.8,
    auction_single_time_seconds=0.3,
)
metrics = build_run_metrics([local_assignment, cross_assignment], 2, [report])
assert metrics.total_revenue == metrics.local_revenue + metrics.cross_revenue
assert metrics.local_revenue == local_assignment.local_platform_revenue
assert metrics.cross_revenue == cross_assignment.local_platform_revenue
assert metrics.auction_full_time == 0.8
assert metrics.auction_single_time == 0.3
```

Extend CAPA summary tests to expect:

```python
assert summary["metrics"]["local_TR"] == 8.0
assert summary["metrics"]["cross_TR"] == 7.5
assert summary["metrics"]["AT_full"] == expected_full
assert summary["metrics"]["AT_single"] == expected_single
```

Add a DAPA timing test using a timing accumulator and a deterministic auction,
asserting DAPA increments both auction counters and
`auction_full_time_seconds >= auction_single_time_seconds >= 0.0`.

**Step 2: Verify tests fail**

Run:

```bash
python3 -m pytest -q tests/test_metric_alignment.py tests/test_algorithm_summary_fields.py tests/test_capa_auction.py
```

Expected: failures because new timing/revenue fields and output keys do not
exist.

**Step 3: Implement minimal CAPA metric support**

Extend timing dataclasses with DAPA-only fields; have `run_dapa()` calculate
full elapsed and exclusion-adjusted single elapsed once, adding both to the
timing accumulator while continuing to add the single value to current
decision time. Add local/cross revenue and auction mean aggregators in
`capa.metrics`, extend `RunMetrics`, and map fields to CAPA output metric keys.

**Step 4: Verify tests pass**

Run the Task 2 pytest command and confirm it passes.

**Step 5: Commit**

```bash
git add capa/models.py capa/utility.py capa/dapa.py capa/metrics.py algorithms/capa_runner.py tests/test_metric_alignment.py tests/test_algorithm_summary_fields.py tests/test_capa_auction.py
git commit -m "feat(capa): report revenue split and dapa auction timing"
```

### Task 3: Propagate Revenue Split Across Non-CAPA Outputs

**Files:**
- Modify: `baselines/common.py`
- Modify: `baselines/greedy.py`
- Modify: `baselines/mra.py`
- Modify: `baselines/gta.py`
- Modify: `baselines/ramcom.py`
- Modify: `rl_capa/evaluate_core.py`
- Modify: `rl_capa/evaluate.py`
- Modify: `tests/test_algorithm_summary_fields.py`
- Modify: `tests/test_rl_env_smoke.py`
- Modify: `tests/test_metric_alignment.py`

**Step 1: Write failing tests**

Extend baseline summary and behavior tests so local-only metrics include:

```python
assert metrics["local_TR"] == metrics["TR"]
assert metrics["cross_TR"] == 0.0
assert "AT_full" not in metrics
assert "AT_single" not in metrics
```

For cross-capable GTA/RamCOM and RL evaluation, construct or use delivered
local/cross outcomes and assert `TR == local_TR + cross_TR`. Also assert
non-CAPA outputs do not expose CAPA auction timing keys.

**Step 2: Verify tests fail**

Run:

```bash
python3 -m pytest -q tests/test_algorithm_summary_fields.py tests/test_metric_alignment.py tests/test_rl_env_smoke.py
```

Expected: failures for missing `local_TR` and `cross_TR` in non-CAPA metric
payloads.

**Step 3: Implement minimal propagation**

Add a shared delivered-revenue mode splitter for baselines and use it where
delivered identifiers and assignment modes are already computed. Add direct
local-only fields for Greedy and MRA. Extend RL evaluation results to calculate
and average delivered local/cross revenue alongside existing `TR`.

**Step 4: Verify tests pass**

Run the Task 3 pytest command and confirm it passes.

**Step 5: Commit**

```bash
git add baselines/common.py baselines/greedy.py baselines/mra.py baselines/gta.py baselines/ramcom.py rl_capa/evaluate_core.py rl_capa/evaluate.py tests/test_algorithm_summary_fields.py tests/test_metric_alignment.py tests/test_rl_env_smoke.py
git commit -m "feat(metrics): expose local and cross revenue components"
```

### Task 4: Final Verification

**Files:**
- Review all files changed by Tasks 1-3.

**Step 1: Inspect diff and status**

Run:

```bash
git status --short --branch
git diff --stat HEAD~3..HEAD
```

**Step 2: Run focused metric and experiment tests**

Run:

```bash
python3 -m pytest -q tests/test_paper_experiment_presets.py tests/test_metric_alignment.py tests/test_algorithm_summary_fields.py tests/test_capa_auction.py tests/test_rl_env_smoke.py
```

**Step 3: Run broader regression tests**

Run:

```bash
python3 -m pytest -q tests
```

If pre-existing stale assertions fail, report them precisely and do not mask
them by changing unrelated behavior.

**Step 4: Confirm configuration resolution**

Run a small Python probe for `formal` and `ny` parser output and report the
resolved courier/background/deadline defaults.

