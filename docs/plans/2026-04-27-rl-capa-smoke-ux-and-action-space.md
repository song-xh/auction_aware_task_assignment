# RL-CAPA Smoke UX And Action Space Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add explicit RL batch action sets, document the dense `0-30s` smoke window, and show training progress during RL-CAPA runs.

**Architecture:** Keep the Chengdu environment semantics unchanged and make the smoke behavior explicit at the RL runner boundary. Add one new optional CLI/config path for discrete batch actions, thread it through the RL runner/config/trainer stack, and add progress rendering in the training entrypoint without changing the environment core. Document the `0-30s` dense-window smoke command instead of silently changing global environment defaults.

**Tech Stack:** Python, argparse, unittest, tqdm, existing RL-CAPA runner/config/trainer modules

---

### Task 1: Add Explicit RL Batch Actions

**Files:**
- Modify: `runner.py`
- Modify: `algorithms/rl_capa_runner.py`
- Modify: `rl_capa/config.py`
- Test: `tests/test_rl_env_smoke.py`

**Step 1: Write the failing test**

Add tests that:
- construct `RLCAPAConfig(batch_actions=[10, 15, 20])` and assert `batch_action_values()` returns `[10, 15, 20]`
- verify invalid explicit action lists are rejected
- verify runner argument translation prefers explicit `rl_batch_actions` over `min/max`

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_rl_env_smoke -v`

Expected: FAIL because explicit action-list support does not exist yet.

**Step 3: Write minimal implementation**

Implement:
- optional `batch_actions: tuple[int, ...] | None` in `RLCAPAConfig`
- validation that explicit actions are positive, unique, and sorted-preserving
- `runner.py --rl-batch-actions` CLI argument
- `build_algorithm_kwargs()` pass-through
- `algorithms/rl_capa_runner.py` support for explicit action lists while keeping `min/max` compatibility

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_rl_env_smoke -v`

Expected: PASS

**Step 5: Commit**

```bash
git add runner.py algorithms/rl_capa_runner.py rl_capa/config.py tests/test_rl_env_smoke.py docs/plans/2026-04-27-rl-capa-smoke-ux-and-action-space.md
git commit -m "feat(rl-capa): support explicit batch action sets"
```

### Task 2: Document The Dense 0-30s Smoke Window

**Files:**
- Modify: `README.md`
- Test: manual command validation with the unified runner help/parse path

**Step 1: Write the failing test**

There is no clean automated doc test in this repo for README examples, so use a CLI parse verification instead:
- confirm the new smoke command with `--task-window-start-seconds 0 --task-window-end-seconds 30 --rl-batch-actions ...` parses successfully

**Step 2: Run parse command to verify the current UX is incomplete**

Run:

```bash
python3 runner.py run --algorithm rl-capa --data-dir Data --num-parcels 100 --local-couriers 10 --platforms 2 --couriers-per-platform 5 --task-window-start-seconds 0 --task-window-end-seconds 30 --rl-batch-actions 10 15 20 --episodes 1 --output-dir /tmp/rl_capa_cli_smoke
```

Expected: before Task 1 is complete, parse should fail on `--rl-batch-actions`.

**Step 3: Write minimal implementation**

Update the README RL-CAPA example and parameter notes to:
- recommend `--task-window-start-seconds 0`
- recommend `--task-window-end-seconds 30`
- recommend `--rl-batch-actions 10 15 20`
- explain that this is a smoke-oriented dense-window recipe, not the global default behavior

**Step 4: Run parse command to verify it now works**

Run the same CLI command after Task 1.

Expected: command starts successfully and enters runtime.

**Step 5: Commit**

```bash
git add README.md
git commit -m "docs(rl-capa): document dense 0-30s smoke command"
```

### Task 3: Add RL-CAPA Training Progress Rendering

**Files:**
- Modify: `rl_capa/train.py`
- Modify: `rl_capa/trainer.py`
- Modify: `algorithms/rl_capa_runner.py`
- Test: `tests/test_rl_env_smoke.py`

**Step 1: Write the failing test**

Add tests that:
- inject a simple progress callback into training
- assert one progress event per episode is emitted with episode index and summary fields

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_rl_env_smoke -v`

Expected: FAIL because training currently exposes no progress callback/events.

**Step 3: Write minimal implementation**

Implement:
- optional trainer progress callback interface
- per-episode progress payloads including episode number, total episodes, reward, steps, assignments, average batch size, and truncation flag
- `tqdm` rendering in `train_rl_capa()` for user-facing CLI runs
- preserve a callback path so future experiment orchestration can consume structured progress

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_rl_env_smoke -v`

Expected: PASS

**Step 5: Commit**

```bash
git add rl_capa/train.py rl_capa/trainer.py algorithms/rl_capa_runner.py tests/test_rl_env_smoke.py
git commit -m "feat(rl-capa): show training progress"
```

### Task 4: End-To-End Smoke Verification

**Files:**
- No additional code changes required unless verification exposes regressions

**Step 1: Run focused unit coverage**

Run: `python3 -m unittest tests.test_rl_env_smoke -v`

Expected: PASS

**Step 2: Run one RL-CAPA smoke command**

Run:

```bash
python3 -u runner.py run \
  --algorithm rl-capa \
  --data-dir Data \
  --num-parcels 100 \
  --local-couriers 10 \
  --platforms 2 \
  --couriers-per-platform 5 \
  --task-window-start-seconds 0 \
  --task-window-end-seconds 30 \
  --rl-batch-actions 10 15 20 \
  --episodes 1 \
  --output-dir outputs/plots/rl_capa_smoke_dense_progress
```

Expected:
- command starts successfully
- training progress is visible during the run
- `summary.json` is written

**Step 3: Commit follow-up fixes if needed**

Only if verification exposes defects.
