# CAPA Config Centralization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Centralize CAPA paper defaults, Chengdu adapter defaults, and baseline-private defaults into `capa/config.py`, then update callers to read those defaults from one place without changing algorithm behavior.

**Architecture:** Add one configuration module that exposes grouped constants plus a few helper builders for CAPA experiment presets and Chengdu platform defaults. Keep `CAPAConfig` and runner interfaces unchanged, but replace scattered literals and duplicated default constants with imports from the centralized module.

**Tech Stack:** Python, `unittest`, existing CAPA/Chengdu experiment modules.

---

### Task 1: Lock Down the Desired Defaults With Tests

**Files:**
- Create: `tests/test_capa_config.py`
- Modify: none
- Test: `tests/test_capa_config.py`

**Step 1: Write the failing test**

Add tests that assert:
- `CAPAConfig()` uses the centralized CAPA paper defaults.
- `build_default_chengdu_config()` returns the same centralized defaults for a supplied `batch_size`.
- `DEFAULT_EXP1_ROUNDS` reuses the centralized paper-default and sensitivity presets instead of independent literals.
- `legacy_courier_to_capa()` and `project_courier_to_capa()` use the same centralized courier fallback defaults.
- Chengdu platform helper builders return the expected base-price, sharing-rate, and quality dictionaries.

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_capa_config -v`

Expected: FAIL because `capa.config` and the centralized references do not exist yet.

**Step 3: Commit**

Do not commit yet. Continue to the implementation tasks once the failure is confirmed.

### Task 2: Add the Centralized Configuration Module

**Files:**
- Create: `capa/config.py`
- Modify: `capa/models.py`
- Modify: `capa/utility.py`
- Modify: `capa/revenue.py`
- Test: `tests/test_capa_config.py`

**Step 1: Write minimal implementation**

Add `capa/config.py` with three clearly separated sections:
- Paper CAPA defaults
- Chengdu adapter defaults
- Baseline-specific defaults

Expose:
- CAPA paper constants for `gamma`, `omega`, `zeta`, `mu1`, `mu2`, and default batch size.
- Chengdu adapter constants for courier preference / alpha / beta / service score.
- Baseline defaults for Greedy, GTA, MRA, and RamCOM.
- Helper builders for CAPA runner kwargs presets and Chengdu platform dictionaries.

Update:
- `capa/models.py` so `CAPAConfig` defaults come from `capa.config`.
- `capa/utility.py` and `capa/revenue.py` so the shared local payment ratio aligns with the centralized `zeta`.

**Step 2: Run tests**

Run: `python -m unittest tests.test_capa_config -v`

Expected: Some tests still fail until the remaining callers stop using local literals.

### Task 3: Replace Scattered CAPA And Chengdu Defaults

**Files:**
- Modify: `algorithms/capa_runner.py`
- Modify: `capa/experiments.py`
- Modify: `experiments/paper_chengdu.py`
- Modify: `env/chengdu.py`
- Modify: `baselines/common.py`
- Test: `tests/test_capa_config.py`

**Step 1: Write minimal implementation**

Replace duplicated defaults and literal dictionaries with imports from `capa.config`:
- CAPA runner constructor and factory defaults
- Chengdu experiment config builder
- Exp-1 managed round presets
- Chengdu courier fallback defaults
- Chengdu seeded preference default
- Chengdu platform base price / sharing rate / quality defaults
- Shared courier fallback path in baseline helpers

**Step 2: Run tests**

Run: `python -m unittest tests.test_capa_config -v`

Expected: PASS.

### Task 4: Replace Baseline-Private Default Sources

**Files:**
- Modify: `baselines/greedy.py`
- Modify: `baselines/gta.py`
- Modify: `baselines/mra.py`
- Modify: `baselines/ramcom.py`
- Modify: `algorithms/impgta_runner.py`
- Modify: `algorithms/ramcom_runner.py`
- Modify: `baselines/__init__.py`
- Test: `tests/test_capa_config.py`

**Step 1: Write minimal implementation**

Import baseline-specific defaults from `capa.config` and remove duplicated module-level literals where possible, including:
- Greedy utility / realtime defaults and the legacy greedy base bid offset.
- GTA unit-price-per-km and ImpGTA prediction-window defaults.
- MRA base price and sharing rate defaults.
- RamCOM random-seed default.

Retain behavior by only changing default-value sources.

**Step 2: Run focused tests**

Run: `python -m unittest tests.test_capa_config tests.test_capa_local tests.test_capa_auction tests.test_mra_bpt -v`

Expected: PASS.

### Task 5: Final Verification And Commit

**Files:**
- Modify: none
- Test: existing targeted suite

**Step 1: Run verification**

Run: `python -m unittest tests.test_capa_config tests.test_capa_local tests.test_capa_auction tests.test_capa_warmup tests.test_mra_bpt tests.test_graph_utils_chengdu -v`

Expected: PASS.

**Step 2: Inspect the worktree**

Run: `git status --short`

Expected: only the intended config, caller, test, and plan-doc changes.

**Step 3: Commit**

```bash
git add capa/config.py capa/models.py capa/utility.py capa/revenue.py algorithms/capa_runner.py capa/experiments.py experiments/paper_chengdu.py env/chengdu.py baselines/common.py baselines/greedy.py baselines/gta.py baselines/mra.py baselines/ramcom.py algorithms/impgta_runner.py algorithms/ramcom_runner.py baselines/__init__.py tests/test_capa_config.py docs/plans/2026-04-09-capa-config-centralization.md
git commit -m "refactor(capa): centralize experiment parameter defaults"
```
