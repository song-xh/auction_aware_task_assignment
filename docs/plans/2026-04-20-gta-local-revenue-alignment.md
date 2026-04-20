# GTA Local Revenue Alignment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Prove and, if necessary, repair BaseGTA/ImpGTA so their local-task TR is evaluated with the same CAPA local-platform revenue rule `p_tau - Rc(tau,c)` rather than raw fare.

**Architecture:** Audit the current GTA baseline adapter first. If the code already uses the unified CAPA revenue helper, avoid unnecessary behavior changes and instead add explicit regression tests. Only modify production code if the tests expose a mismatch.

**Tech Stack:** Python, unified Chengdu baseline adapters, local unittest verification.

---

### Task 1: Lock the expected local-revenue behavior with failing-or-proving tests

**Files:**
- Modify: `tests/test_metric_alignment.py`

**Step 1: Add targeted tests**
Add regression tests proving:
- BaseGTA local assignment TR equals `fare - zeta * fare`
- ImpGTA local assignment TR equals `fare - zeta * fare`
- Cross-assignment AIM payment test remains intact

**Step 2: Run the tests**
Run:
```bash
python3 -m unittest tests.test_metric_alignment -v
```

**Step 3: If production behavior already matches, do not change it**
Only proceed to production edits if a test fails.

**Step 4: Commit the test checkpoint**
```bash
git add -f tests/test_metric_alignment.py docs/plans/2026-04-20-gta-local-revenue-alignment.md
git commit -m "test(gta): lock local revenue alignment with capa"
```

### Task 2: Repair production code only if tests expose mismatch

**Files:**
- Modify: `baselines/gta.py` (only if required)

**Step 1: Keep GTA method logic unchanged**
Do not alter:
- local-first dispatch
- AIM winner/payment
- ImpGTA future-window participation logic

**Step 2: Ensure local TR uses CAPA revenue**
If needed, route BaseGTA/ImpGTA local assignment accounting through:
- `compute_local_platform_revenue_for_local_completion()`
with the configured `local_payment_ratio`

**Step 3: Run verification**
Run:
```bash
python3 -m unittest tests.test_metric_alignment -v
python3 -m py_compile baselines/gta.py
```

**Step 4: Commit if code changed**
```bash
git add baselines/gta.py && git add -f tests/test_metric_alignment.py
git commit -m "fix(gta): align local revenue accounting with capa"
```
