# ImpGTA AIM Alignment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Re-align `ImpGTA` with reference `[17]` so its cross-platform bidding and settlement use GTA's `AIM` auction rather than CAPA's `DAPA/DLAM`, while preserving the current prediction-success-rate mechanism and CAPA-aligned local-platform revenue accounting.

**Architecture:** Keep the existing unified Chengdu environment and the current `BaseGTA`/`ImpGTA` shared runner in `baselines/gta.py`. Narrow the behavioral change to the `ImpGTA` outer-settlement path: prediction gating stays in place, but once partner platforms qualify, the winner and critical payment are determined by `AIM` using the existing GTA bids rather than converting partners into CAPA platforms and invoking `run_dapa()`.

**Tech Stack:** Python, `unittest`/`pytest`, existing Chengdu legacy environment adapters, GTA baseline runner.

---

### Task 1: Lock the intended ImpGTA/AIM behavior in tests

**Files:**
- Modify: `tests/test_metric_alignment.py`
- Reference: `baselines/gta.py`

**Step 1: Replace the existing ImpGTA cross-settlement expectation tests**

Update the tests that currently assert:
- `ImpGTA` must reuse `CAPA/DLAM` payment
- `ImpGTA` must not call `AIM`
- `ImpGTA` BPT excludes `DLAM` routing delay

with new expectations that assert:
- `ImpGTA` cross settlement uses `AIM` critical payment
- `ImpGTA` calls `settle_aim_auction()` on the cross path
- `ImpGTA` `TR` still uses `compute_local_platform_revenue_for_cross_completion()` with the `AIM` platform payment
- `ImpGTA` BPT remains routing/insertion-excluded under the `AIM` path

**Step 2: Add a focused regression for prediction plus AIM**

Add one regression where:
- local platform rejects a task locally,
- two outer platforms pass the prediction gate,
- bids differ,
- `ImpGTA` selects the lowest-dispatch-cost winner and pays the second-lowest critical price plus sharing surcharge capped by fare, exactly as `AIM` does.

**Step 3: Run the targeted tests and verify they fail before implementation**

Run:

```bash
pytest tests/test_metric_alignment.py -q
```

Expected: failures in the ImpGTA-specific assertions because the implementation still uses `DAPA/DLAM`.

**Step 4: Commit the failing-test update only after implementation passes**

This task's commit will happen together with the implementation commit to avoid committing a broken branch snapshot.


### Task 2: Rewire ImpGTA cross settlement from DAPA back to AIM

**Files:**
- Modify: `baselines/gta.py`

**Step 1: Remove the ImpGTA-only DLAM settlement helper**

Delete or replace:

- `settle_dlam_auction_for_impgta(...)`

so `ImpGTA` no longer converts partner platforms into CAPA platform snapshots just to settle one outer assignment.

**Step 2: Preserve the current prediction gating logic**

Do not change:

- `future_tasks_within_window(...)`
- `platform_prediction_sampling_seed(...)`
- `should_dispatch_inner_task_impgta(...)`
- `should_bid_outer_platform_impgta(...)`

The only semantic change in this task is the auction rule after platforms pass the outer condition.

**Step 3: Build explicit AIM bids for ImpGTA**

In `_run_gta_environment(...)`:

- keep collecting `partner_bid` with `select_available_courier_for_task(...)`
- when `algorithm == "impgta"` and the outer condition passes, append a `GTABid` entry to an `outer_bids` list
- do not build `dlam_platform_ids`

**Step 4: Settle ImpGTA with AIM**

In the `algorithm == "impgta"` branch:

- call `settle_aim_auction(...)` with the filtered `outer_bids`
- apply the chosen courier and insertion index exactly as `BaseGTA` already does

**Step 5: Keep revenue accounting aligned with CAPA**

Do not change the `TR` bookkeeping:

- local completion still uses `compute_local_platform_revenue_for_local_completion(...)`
- cross completion still uses `compute_local_platform_revenue_for_cross_completion(parcel_fare, outcome.payment)`

This preserves the current repository-wide metric alignment while changing only the bidding rule.

**Step 6: Run the targeted regression suite**

Run:

```bash
pytest tests/test_metric_alignment.py -q
```

Expected: PASS.

**Step 7: Commit**

```bash
git add baselines/gta.py tests/test_metric_alignment.py
git commit -m "fix(impgta): restore aim auction settlement"
```


### Task 3: Verify runner-level integration and merge readiness

**Files:**
- Modify: `docs/review_0427.md` only if the final conclusions need a short correction note
- Reference: `algorithms/impgta_runner.py`

**Step 1: Run the broader targeted baseline coverage**

Run:

```bash
pytest tests/test_metric_alignment.py tests/test_algorithm_summary_fields.py tests/test_capa_config.py -q
```

Expected: PASS.

**Step 2: Run one small ImpGTA smoke execution if needed**

If the unit tests pass but the runtime path is still uncertain, run one small command that exercises the unified runner with `impgta` and verify it returns without raising.

**Step 3: Check git status**

Run:

```bash
git status --short --branch
```

Expected: only the intended tracked files are modified or added.

**Step 4: Merge back to `master` after verification**

From the main worktree:

```bash
git merge --ff-only feat/impgta-aim-alignment
```

Expected: fast-forward merge with a clean `master`.
