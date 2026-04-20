# GTA Fairness Alignment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove the remaining unfair TR advantage of `BaseGTA` and `ImpGTA` over `CAPA` by aligning GTA-family evaluation to the same CPUL revenue semantics while keeping GTA matching logic based on AIM.

**Architecture:** Keep `BaseGTA` and `ImpGTA` winner selection and AIM auction behavior intact, but correct the CPUL adaptation points that feed their revenue accounting. The work centers on `baselines/gta.py`, adds focused regression tests, and uses tiny Chengdu experiment reruns to confirm metric movement before each commit.

**Tech Stack:** Python, `unittest`, current Chengdu experiment runners under `experiments/`.

---

### Task 1: Lock the current bug with failing GTA fairness tests

**Files:**
- Modify: `tests/test_metric_alignment.py`
- Reference: `baselines/gta.py`, `capa/utility.py`, `docs/review_0421_result.md`

**Step 1: Write failing tests for cross-platform revenue semantics**

Add tests that prove:
- GTA cross-platform revenue must equal `fare - (critical_payment + mu2 * fare)` rather than `fare - critical_payment`
- The returned `AIMOutcome.payment` must represent the amount paid to the cooperating platform, not only the courier wage

**Step 2: Write failing tests for CPUL incremental dispatch cost**

Add tests that prove:
- For a courier with an existing route, GTA dispatch cost must use insertion increment `Δdist`, not plain `ready_location -> pickup`
- Idle couriers still reduce to direct distance

**Step 3: Run the targeted test file and verify RED**

Run: `python3 -m unittest discover -s tests -p 'test_metric_alignment.py' -v`

Expected:
- New GTA fairness tests fail
- Existing metric-alignment tests still run

**Step 4: Commit the red-state scaffolding together with the two pending review docs and this plan**

Commit includes:
- `docs/review_0421.md`
- `docs/review_0421_result.md`
- `docs/plans/2026-04-21-review-0421-gta-fairness.md`
- updated failing tests

Commit message:

```bash
git add docs/review_0421.md docs/review_0421_result.md docs/plans/2026-04-21-review-0421-gta-fairness.md tests/test_metric_alignment.py
git commit -m "test(gta): lock fairness regression findings from review_0421"
```

### Task 2: Fix GTA cross-platform payment semantics

**Files:**
- Modify: `baselines/gta.py`
- Reference: `capa/config.py`, `capa/utility.py`
- Test: `tests/test_metric_alignment.py`

**Step 1: Introduce explicit platform-level cross payment**

Adjust AIM settlement so that:
- winner selection remains the same
- critical courier dispatch cost remains the same
- returned platform payment becomes `min(fare, critical_payment + mu2 * fare)`

Use centralized CAPA sharing defaults from `capa/config.py` rather than duplicating constants.

**Step 2: Thread the shared `mu2` parameter through GTA runners**

Update:
- `run_basegta_baseline_environment(...)`
- `run_impgta_baseline_environment(...)`
- internal `_run_gta_environment(...)`

Keep defaults centralized and paper-consistent.

**Step 3: Re-run targeted unit tests and verify GREEN**

Run:
- `python3 -m unittest discover -s tests -p 'test_metric_alignment.py' -v`

Expected:
- Cross-payment tests now pass
- Existing local-revenue alignment tests remain green

**Step 4: Run a tiny experiment sanity check**

Run a small `Exp-1` point with:
- `num_parcels=20`
- a reduced courier/platform configuration

Expected:
- `BaseGTA/ImpGTA` still complete
- `TR` for `ImpGTA` drops relative to the pre-fix behavior
- No regression in JSON structure

**Step 5: Commit**

```bash
git add baselines/gta.py tests/test_metric_alignment.py
git commit -m "fix(gta): align cross-platform payment with capa revenue semantics"
```

### Task 3: Fix GTA CPUL dispatch-cost adaptation to use insertion increment

**Files:**
- Modify: `baselines/gta.py`
- Reference: `capa/utility.py`, `capa/cache.py`, `capa/constraints.py`
- Test: `tests/test_metric_alignment.py`

**Step 1: Implement CPUL incremental dispatch-cost helper**

Add a helper that computes dispatch cost from the best insertion increment:
- idle courier: direct pickup distance
- routed courier: `min_k (d(r_k,p) + d(p,r_k+1) - d(r_k,r_k+1))`

Use the existing travel model and keep AIM decision semantics intact.

**Step 2: Replace direct-distance bid construction**

Update:
- `select_idle_courier_for_task(...)`
- `select_available_courier_for_task(...)`

so that their `dispatch_cost` comes from the new incremental helper.

**Step 3: Preserve feasibility semantics**

Do not relax deadline/radius checks. If exact insertion-time feasibility is too invasive for this change, keep the current feasibility gate and only correct the bid-cost semantics in this task.

**Step 4: Re-run targeted tests and verify GREEN**

Run:
- `python3 -m unittest discover -s tests -p 'test_metric_alignment.py' -v`

Expected:
- Incremental-cost tests pass
- Prior GTA metric tests stay green

**Step 5: Run another tiny `Exp-1` comparison**

Expected:
- GTA `TR` moves further toward CAPA
- No crash in BaseGTA/ImpGTA execution

**Step 6: Commit**

```bash
git add baselines/gta.py tests/test_metric_alignment.py
git commit -m "fix(gta): use insertion-based dispatch cost in cpul adaptation"
```

### Task 4: Re-check `env/chengdu.py` and metric surfaces after GTA changes

**Files:**
- Review/modify only if needed: `env/chengdu.py`, `capa/metrics.py`
- Test: `tests/test_metric_alignment.py`, `tests/test_mra_bpt.py`, `tests/test_capa_config.py`

**Step 1: Re-audit delivered counting and summary fields**

Confirm that GTA-family changes did not reintroduce drift in:
- `delivered_parcels`
- `accepted_assignments`
- `CR`
- `BPT`

**Step 2: Run regression suite**

Run:
- `python3 -m unittest discover -s tests -p 'test_metric_alignment.py' -v`
- `python3 -m unittest tests.test_mra_bpt tests.test_capa_config -v`

Expected:
- All pass

**Step 3: Commit only if code changes were required**

```bash
git add env/chengdu.py capa/metrics.py tests/test_metric_alignment.py
git commit -m "fix(env): keep unified metric surfaces after gta fairness changes"
```

### Task 5: Final experiment verification and branch closeout

**Files:**
- Output only: temporary `/tmp/*` or chosen result staging directory

**Step 1: Run a small-sample formal-style check**

Run a reduced `Exp-1` split or point experiment that includes:
- `capa`
- `basegta`
- `impgta`

Expected:
- All complete
- `BaseGTA/ImpGTA` no longer get inflated cross TR from courier-only payment semantics

**Step 2: Summarize the before/after behavior**

Check:
- `TR`
- `CR`
- `TR / delivered`

**Step 3: Verify clean branch state**

Run:
- `git status --short`

Expected:
- clean working tree

**Step 4: Report results and integration readiness**

Only after the verification commands pass, report completion and offer merge/push options if requested.
