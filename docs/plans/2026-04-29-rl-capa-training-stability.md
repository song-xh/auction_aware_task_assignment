# RL-CAPA Training Stability Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make RL-CAPA training diagnostics and default optimization more robust so cross-rate collapse can be distinguished from plot smoothing or parameter choice.

**Architecture:** Keep the unified Chengdu environment and actor-critic algorithm unchanged. Add episode-level diagnostics, optional advantage normalization, and README guidance for less saturated RL-CAPA runs.

**Tech Stack:** Python dataclasses, unittest, PyTorch, matplotlib, unified `runner.py` CLI.

---

### Task 1: Add Training Diagnostics

**Files:**
- Modify: `rl_capa/trainer.py`
- Modify: `rl_capa/train.py`
- Modify: `rl_capa/visualize.py`
- Test: `tests/test_rl_training_progress.py`
- Test: `tests/test_rl_output_artifacts.py`

**Steps:**
1. Add failing tests that require progress payloads and summaries to include policy entropies and mean batch size.
2. Add `entropy_1`, parcel-normalized `entropy_2`, and `mean_batch_size` to `EpisodeLog`.
3. Write those fields into `training_summary.json`.
4. Plot entropy in the previously unused subplot and make raw trajectories more visible.
5. Run targeted RL-CAPA tests.
6. Commit as `fix(rl-capa): expose training stability diagnostics`.

### Task 2: Add Advantage Normalization Control

**Files:**
- Modify: `rl_capa/config.py`
- Modify: `rl_capa/trainer.py`
- Modify: `rl_capa/train.py`
- Modify: `algorithms/rl_capa_runner.py`
- Modify: `runner.py`
- Test: `tests/test_rl_runner_ux.py`

**Steps:**
1. Add failing tests for CLI propagation of a new `--rl-disable-advantage-normalization` flag and the trainer normalization helper.
2. Add `normalize_advantages` to config dataclasses, defaulting to `True`.
3. Standardize detached advantages before actor losses when enabled.
4. Preserve a CLI switch to disable it for exact ablation/reproduction.
5. Run targeted RL-CAPA tests.
6. Commit as `fix(rl-capa): stabilize actor advantage scaling`.

### Task 3: Update README Guidance

**Files:**
- Modify: `README.md`
- Test: `tests/test_rl_runner_ux.py`

**Steps:**
1. Add README checks for the stable RL-CAPA command and the new flag.
2. Document why long high-learning-rate runs can converge to cross-rate zero when local matching is sufficient.
3. Provide a recommended anti-collapse CLI recipe with lower actor LR, higher entropy, and fewer episodes.
4. Run README/runner tests.
5. Commit as `docs: document stable rl-capa training recipe`.

