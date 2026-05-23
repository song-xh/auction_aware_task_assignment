# RL-CAPA Service Slack Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add an optional `service_slack` feature to RL-CAPA Stage-2 state without changing existing local/cross execution semantics.

**Architecture:** Extend `RLCAPAConfig` with a boolean feature flag, compute one normalized per-parcel slack value inside the RL environment using the existing local travel-time and feasibility helpers, and make Stage-2 network dimensions depend on the flag. Preserve old behavior and checkpoint compatibility when the flag is disabled; raise a clear error on checkpoint dimension mismatch when it is enabled against old weights.

**Tech Stack:** Python, dataclasses, PyTorch, unittest/pytest-style regression tests.

---

### Task 1: Add failing config and CLI tests

**Files:**
- Modify: `tests/test_rl_runner_ux.py`

**Step 1: Write the failing test**

Add tests that assert:
- `RLCAPAConfig(..., use_service_slack=True)` stores the flag.
- `runner.parse_args(...)` accepts `--rl-use-service-slack`.
- `build_algorithm_kwargs(...)` forwards `use_service_slack=True` for `rl-capa`, `rl-capa-stage2`, and `rl-capa-infer`.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_rl_runner_ux.py -q`
Expected: FAIL because the flag is not implemented yet.

**Step 3: Write minimal implementation**

Update:
- `rl_capa/config.py`
- `runner.py`
- RL runner constructors that build `RLCAPAConfig`

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_rl_runner_ux.py -q`
Expected: PASS

### Task 2: Add failing Stage-2 state tests

**Files:**
- Modify: `tests/test_rl_env_smoke.py`

**Step 1: Write the failing test**

Add tests that assert:
- default Stage-2 state shape stays `(9,)`
- enabling `use_service_slack=True` changes Stage-2 state shape to `(10,)`
- a parcel with reachable local courier has positive clipped slack
- no eligible local courier yields normalized slack `-1.0`
- action semantics remain unchanged; this is state-only

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_rl_env_smoke.py -q`
Expected: FAIL because the new state feature does not exist yet.

**Step 3: Write minimal implementation**

Update:
- `rl_capa/state_builder.py`
- `rl_capa/env.py`
- reuse `capa.cama.is_courier_available`, capacity checks, service-radius checks, and the shared travel model

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_rl_env_smoke.py -q`
Expected: PASS

### Task 3: Add failing checkpoint compatibility tests

**Files:**
- Modify: `tests/test_rl_output_artifacts.py`

**Step 1: Write the failing test**

Add a test that simulates loading an old 9D Stage-2 checkpoint into a `use_service_slack=True` configuration and asserts the loader raises a clear `ValueError` containing:

`Checkpoint state dimension does not match current Stage-2 state dimension`

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_rl_output_artifacts.py -q`
Expected: FAIL because load-time validation is missing.

**Step 3: Write minimal implementation**

Update:
- `rl_capa/trainer.py`
- `rl_capa/evaluate.py` if needed only for plumbing, not behavior changes

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_rl_output_artifacts.py -q`
Expected: PASS

### Task 4: Wire dynamic Stage-2 dimensions through trainers and summaries

**Files:**
- Modify: `rl_capa/trainer.py`
- Modify: `rl_capa/stage2_trainer.py`
- Modify: `rl_capa/networks.py`
- Modify: `rl_capa/train.py`
- Modify: `rl_capa/train_stage2.py`
- Modify: `algorithms/rl_capa_runner.py`
- Modify: `algorithms/rl_capa_stage2_runner.py`
- Modify: `algorithms/rl_capa_infer_runner.py`

**Step 1: Write minimal implementation**

Make Stage-2 actor/critic input dimensions and zero tensors depend on the config flag instead of the global constant.

Add summary/config metadata:
- `use_service_slack`
- optional variant label such as `rl-capa-svc` / `rl-capa-stage2-svc` when enabled

**Step 2: Run focused tests**

Run:
- `pytest tests/test_rl_runner_ux.py -q`
- `pytest tests/test_rl_env_smoke.py -q`
- `pytest tests/test_rl_output_artifacts.py -q`

Expected: PASS

### Task 5: Effect check

**Files:**
- No new file required unless a small note is needed after verification

**Step 1: Run a small smoke/effect check**

Run one tiny scripted check or one focused unit assertion proving:
- `use_service_slack=False` keeps Stage-2 shape at 9
- `use_service_slack=True` makes it 10
- the same batch still routes `a=0` to local-first and `a=1` to cross-first

**Step 2: Verify no semantic regression**

Run: `pytest tests/test_rl_env_smoke.py::test_stage2_decisions_apply_to_full_batch_without_cama -q`
Expected: PASS

**Step 3: Commit**

```bash
git add docs/plans/2026-05-23-rl-capa-service-slack.md tests/test_rl_runner_ux.py tests/test_rl_env_smoke.py tests/test_rl_output_artifacts.py rl_capa/config.py rl_capa/state_builder.py rl_capa/env.py rl_capa/trainer.py rl_capa/stage2_trainer.py rl_capa/networks.py rl_capa/train.py rl_capa/train_stage2.py algorithms/rl_capa_runner.py algorithms/rl_capa_stage2_runner.py algorithms/rl_capa_infer_runner.py runner.py
git commit -m "feat(rl-capa): add optional stage2 service slack feature"
```
