# RL-CAPA Inference Paper Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a checkpoint-based `rl-capa-infer` algorithm that runs fixed-policy online inference inside shared Chengdu paper experiments, including exp1-exp6 split workflows.

**Architecture:** Create a dedicated inference-only algorithm runner that wraps `evaluate_rl_capa` and plugs into the existing root registry. Extend CLI/paper override plumbing to pass checkpoint-dir and RL action-space settings into that runner. Validate the integration with unit tests and one real smoke run using the provided checkpoint bundle.

**Tech Stack:** Python, unittest, existing RL-CAPA evaluation/checkpoint utilities, unified experiment registry

---

### Task 1: Document and wire the new algorithm surface

**Files:**
- Modify: `algorithms/registry.py`
- Modify: `runner.py`
- Test: `tests/test_rl_runner_ux.py`

**Step 1:** Add a failing parser test asserting `rl-capa-infer` is a supported algorithm and that `--rl-checkpoint-dir` is forwarded by `build_algorithm_kwargs`.

**Step 2:** Run the targeted test to verify failure.

**Step 3:** Add the registry and CLI support for `rl-capa-infer`.

**Step 4:** Re-run the targeted parser test until it passes.

**Step 5:** Commit.

### Task 2: Implement the eval-only runner

**Files:**
- Create: `algorithms/rl_capa_infer_runner.py`
- Test: `tests/test_rl_output_artifacts.py`

**Step 1:** Add a failing test asserting the inference runner calls `evaluate_rl_capa` without calling `train_rl_capa`, and that it surfaces evaluation metrics/plots in its summary.

**Step 2:** Run the targeted test to verify failure.

**Step 3:** Implement the inference-only runner with checkpoint-dir validation and `evaluate_rl_capa` integration.

**Step 4:** Re-run the targeted test until it passes.

**Step 5:** Commit.

### Task 3: Integrate with paper exp1-exp6 shared-environment flows

**Files:**
- Modify: `experiments/paper_config.py`
- Modify: `experiments/paper_chengdu.py`
- Possibly modify: `experiments/framework/point_runner.py`
- Test: `tests/test_metric_alignment.py`

**Step 1:** Add a failing regression test asserting paper runner overrides can carry `rl-capa-infer` checkpoint settings into point/split runs.

**Step 2:** Run the targeted test to verify failure.

**Step 3:** Add `rl-capa-infer` to the default paper algorithm set and forward checkpoint/feature-window/action-space overrides through paper runner wiring.

**Step 4:** Re-run the targeted test until it passes.

**Step 5:** Commit.

### Task 4: Real checkpoint smoke test

**Files:**
- Output: `outputs/plots/rl_capa_infer_smoke/`

**Step 1:** Run one shared-environment comparison command using the provided checkpoint directory and the same RL parameters used during training.

**Step 2:** Verify the run writes metrics and `summary.json` under the smoke output directory.

**Step 3:** Commit any resulting code changes if this task required them.
