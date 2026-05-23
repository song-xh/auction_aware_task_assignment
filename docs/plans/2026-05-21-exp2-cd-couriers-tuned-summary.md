# Exp2 CD Couriers Tuned Summary Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Aggregate `/mnt/c/Users/songxh/Desktop/result/exp2/exp2_couriers` into a reproducible Chengdu Exp-2 sweep summary with markdown tables and standard TR/CR/BPT plots under `outputs/plots/exp2_cd_couriers_tuned`.

**Architecture:** Add one focused experiment utility that reads per-point `summary.json` files from the external result tree, normalizes them into the repo’s sweep-level `summary.json`, renders a markdown report from the enriched metadata, and reuses `experiments.plotting.save_comparison_plots` for figure generation. Keep the implementation narrow to the current `local_couriers` sweep instead of introducing a premature generic framework.

**Tech Stack:** Python 3, `pathlib`, `json`, `datetime`, `zoneinfo`, existing `experiments.plotting`

---

### Task 1: Lock the output contract with tests

**Files:**
- Create: `tests/test_external_exp2_couriers_summary.py`

**Step 1: Write the failing test**

Cover:
- point directory discovery and numeric ordering
- preferred algorithm ordering
- normalized `summary.json` run structure
- markdown sections and tables
- output file emission through one public write helper

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_external_exp2_couriers_summary.py -q`
Expected: FAIL because the new module does not exist yet.

### Task 2: Implement the aggregator

**Files:**
- Create: `experiments/external_exp2_couriers_summary.py`

**Step 1: Write minimal implementation**

Add:
- source discovery for `point_*`
- preferred algorithm ordering
- metric extraction for `TR`, `CR`, `BPT`, `delivered_parcels`, `accepted_assignments`, `timed_out_parcels`
- timing parsing/formatting to Asia/Shanghai
- markdown rendering helpers
- artifact writer that persists `summary.json`, `summary.md`, and plots
- CLI entrypoint

**Step 2: Run tests to verify they pass**

Run: `pytest tests/test_external_exp2_couriers_summary.py -q`
Expected: PASS

### Task 3: Produce requested artifacts

**Files:**
- Modify: `outputs/plots/exp2_cd_couriers_tuned/*` (generated artifacts)

**Step 1: Run the aggregator against the user-provided source**

Run: `python -m experiments.external_exp2_couriers_summary --source-dir /mnt/c/Users/songxh/Desktop/result/exp2/exp2_couriers --output-dir outputs/plots/exp2_cd_couriers_tuned`

**Step 2: Verify artifacts exist**

Run: `find outputs/plots/exp2_cd_couriers_tuned -maxdepth 1 -type f | sort`
Expected: `summary.json`, `summary.md`, and TR/CR/BPT plot files.

### Task 4: Final verification

**Files:**
- Re-read: `outputs/plots/exp2_cd_couriers_tuned/summary.md`

**Step 1: Run focused tests plus artifact generation command**

Run:
- `pytest tests/test_external_exp2_couriers_summary.py -q`
- `python -m experiments.external_exp2_couriers_summary --source-dir /mnt/c/Users/songxh/Desktop/result/exp2/exp2_couriers --output-dir outputs/plots/exp2_cd_couriers_tuned`

**Step 2: Spot-check markdown content**

Confirm:
- every courier-count setting has a markdown table
- the source path is correct
- the generated plots are referenced at the end
