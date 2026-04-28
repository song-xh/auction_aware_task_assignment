# RL-CAPA Ablations Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add two RL-CAPA ablation trainers and a combined reward-curve runner while reusing the shared Chengdu runtime.

**Architecture:** Keep `rl-capa` unchanged. Add `rl-capa-stage1` for batch-size-only RL with CAPA CAMA/DAPA after each selected batch, `rl-capa-stage2` for fixed-batch parcel-level cross-or-local RL, and `rl-capa-ablation` to run all three policies on one seed and plot reward-vs-episode curves together.

**Tech Stack:** Python, PyTorch actor-critic modules already in `rl_capa`, unittest, matplotlib, unified `runner.py` algorithm registry.

---

### Task 1: Shared Env Hook for CAPA Batch Matching

**Files:**
- Modify: `rl_capa/env.py`
- Test: `tests/test_rl_env_smoke.py`

**Step 1: Write the failing test**

Add a test that calls `RLCAPAEnv.apply_batch_size(10)` followed by `apply_capa_batch()`, verifies accepted assignments are recorded, and verifies a `BatchReport` exists.

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_rl_env_smoke.py -q`

Expected: FAIL because `apply_capa_batch` does not exist.

**Step 3: Write minimal implementation**

Add `RLCAPAEnv.apply_capa_batch()` that reuses `build_chengdu_local_matching_runtime`, `run_cama`, `commit_chengdu_local_assignments`, `run_chengdu_cross_matching`, and `finalize_chengdu_batch`.

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_rl_env_smoke.py -q`

Expected: PASS.

**Step 5: Commit**

Run:
```bash
git add rl_capa/env.py tests/test_rl_env_smoke.py docs/plans/2026-04-29-rl-capa-ablations.md
git commit -m "feat(rl-capa): add capa batch env hook"
```

### Task 2: Stage-1-Only Trainer and Runner

**Files:**
- Create: `rl_capa/stage1_trainer.py`
- Create: `rl_capa/train_stage1.py`
- Create: `algorithms/rl_capa_stage1_runner.py`
- Modify: `algorithms/registry.py`
- Modify: `runner.py`
- Modify: `README.md`
- Test: `tests/test_rl_ablations.py`
- Test: `tests/test_rl_runner_ux.py`

**Step 1: Write failing tests**

Add tests requiring:
- `rl-capa-stage1` is registered.
- `build_algorithm_kwargs()` forwards RL hyperparameters for `rl-capa-stage1`.
- `train_stage1_rl_capa()` returns `episode_returns` and a training plot path.

**Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_rl_ablations tests.test_rl_runner_ux -v`

Expected: FAIL due to missing modules/registry entries.

**Step 3: Implement trainer**

Use `BatchSizeActor` and `StateValueCritic` only. Each episode:
1. Reset `RLCAPAEnv`.
2. Build stage-1 state.
3. Sample batch duration.
4. Call `apply_batch_size(duration)`.
5. Call `apply_capa_batch()`.
6. Use returned step revenue for discounted returns.
7. Update `pi1` and `v1`.

**Step 4: Implement runner and README**

Expose `--algorithm rl-capa-stage1`, reuse existing RL CLI parameters, and document the command.

**Step 5: Run tests and commit**

Run:
```bash
python3 -m unittest tests.test_rl_ablations tests.test_rl_runner_ux -v
git add rl_capa/stage1_trainer.py rl_capa/train_stage1.py algorithms/rl_capa_stage1_runner.py algorithms/registry.py runner.py README.md tests/test_rl_ablations.py tests/test_rl_runner_ux.py
git commit -m "feat(rl-capa): add stage1-only ablation trainer"
```

### Task 3: Stage-2-Only Fixed-Batch Trainer and Runner

**Files:**
- Create: `rl_capa/stage2_trainer.py`
- Create: `rl_capa/train_stage2.py`
- Create: `algorithms/rl_capa_stage2_runner.py`
- Modify: `algorithms/registry.py`
- Modify: `runner.py`
- Modify: `README.md`
- Test: `tests/test_rl_ablations.py`
- Test: `tests/test_rl_runner_ux.py`

**Step 1: Write failing tests**

Add tests requiring:
- `rl-capa-stage2` is registered.
- `build_algorithm_kwargs()` forwards `batch_size` as fixed stage-2 batch size.
- `train_stage2_rl_capa()` returns `episode_returns`, `cross_rate`, and a training plot path.

**Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_rl_ablations tests.test_rl_runner_ux -v`

Expected: FAIL due to missing stage-2 modules/registry entries.

**Step 3: Implement trainer**

Use `CrossOrNotActor` and `ConditionalValueCritic` only. Each step:
1. Call `env.apply_batch_size(fixed_batch_size)`.
2. Build stage-2 states for all eligible parcels.
3. Sample per-parcel Bernoulli actions.
4. Call `env.apply_stage2_decisions(decisions)`.
5. Unresolved local/cross attempts remain in backlog through existing env logic.

**Step 4: Implement runner and README**

Expose `--algorithm rl-capa-stage2`, with `--batch-size 30` as the fixed-batch control.

**Step 5: Run tests and commit**

Run:
```bash
python3 -m unittest tests.test_rl_ablations tests.test_rl_runner_ux -v
git add rl_capa/stage2_trainer.py rl_capa/train_stage2.py algorithms/rl_capa_stage2_runner.py algorithms/registry.py runner.py README.md tests/test_rl_ablations.py tests/test_rl_runner_ux.py
git commit -m "feat(rl-capa): add stage2-only ablation trainer"
```

### Task 4: Combined Ablation Reward Plot

**Files:**
- Create: `rl_capa/ablation_compare.py`
- Create: `algorithms/rl_capa_ablation_runner.py`
- Modify: `algorithms/registry.py`
- Modify: `README.md`
- Test: `tests/test_rl_ablations.py`

**Step 1: Write failing tests**

Add tests requiring `plot_reward_comparison()` to create a plot and `rl-capa-ablation` runner to return `plots.reward_comparison`.

**Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_rl_ablations -v`

Expected: FAIL due to missing comparison plot/runner.

**Step 3: Implement comparison runner**

Build one environment seed, run:
- full `train_rl_capa()`
- `train_stage1_rl_capa()`
- `train_stage2_rl_capa()`

Write each into a subdirectory and plot all three `episode_returns` series in one `reward_comparison.png`.

**Step 4: Run smoke verification**

Run:
```bash
python3 runner.py run --algorithm rl-capa-ablation --data-dir Data --num-parcels 20 --local-couriers 5 --platforms 2 --couriers-per-platform 2 --task-window-start-seconds 0 --task-window-end-seconds 30 --partner-history-task-count-start 20 --partner-history-task-count-step 0 --rl-batch-actions 10 15 --batch-size 30 --episodes 1 --output-dir /tmp/rl_capa_ablation_smoke
```

Expected: command exits 0 and writes `/tmp/rl_capa_ablation_smoke/reward_comparison.png`.

**Step 5: Run tests and commit**

Run:
```bash
python3 -m unittest tests.test_rl_ablations tests.test_rl_runner_ux tests.test_rl_output_artifacts tests.test_rl_training_progress -v
git add rl_capa/ablation_compare.py algorithms/rl_capa_ablation_runner.py algorithms/registry.py README.md tests/test_rl_ablations.py
git commit -m "feat(rl-capa): add combined ablation reward plot"
```

### Task 5: Final Verification and Merge

**Files:**
- No production edits unless verification fails.

**Step 1: Run full tests**

Run: `python3 -m unittest discover -s tests -v`

Expected: PASS.

**Step 2: Merge back**

Run:
```bash
git -C /root/code/auction_aware_task_assignment merge --ff-only feat/rl-capa-ablations
python3 -m unittest tests.test_rl_ablations tests.test_rl_runner_ux -v
```

Expected: PASS on main worktree.

