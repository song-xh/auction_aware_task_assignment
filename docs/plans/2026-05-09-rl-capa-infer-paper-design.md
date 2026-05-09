# RL-CAPA Inference Paper Experiments Design

**Goal:** Allow a trained RL-CAPA checkpoint bundle to participate in Chengdu paper experiments as an online inference baseline on the same shared environment as the heuristic baselines, without retraining.

**Problem:** The codebase already supports RL-CAPA checkpoint evaluation via `rl_capa.evaluate.evaluate_rl_capa`, but the unified algorithm registry and paper experiment framework only expose a training-first `rl-capa` runner. That prevents exp1-exp6 shared-environment comparison runs from reusing a trained checkpoint for fixed-policy online inference.

**Chosen Design:** Introduce a separate algorithm entrypoint named `rl-capa-infer`.

**Why this design:**
- Keeps semantics clean: `rl-capa` remains train-then-evaluate, `rl-capa-infer` is checkpoint-only inference.
- Fits the existing shared-environment framework naturally because all experiment point runners already pass one cloned environment per algorithm.
- Reuses the existing `evaluate_rl_capa` and checkpoint loader instead of duplicating inference logic.

**Behavior:**
- `rl-capa-infer` receives a checkpoint directory and the RL hyperparameters needed to reconstruct action-space shape and trainer config.
- The runner builds a shared-environment seed from the provided environment, loads the checkpointed policy, and performs greedy inference only.
- The runner writes a normal experiment `summary.json` and evaluation plots to its output directory.

**Paper experiment integration:**
- Register `rl-capa-infer` in the root algorithm registry and CLI.
- Make paper experiment scripts and split point runners accept `rl-capa-infer` as a first-class algorithm.
- Add it to the default paper algorithm list so exp1-exp6 can include it without manual per-run overrides.
- Forward `rl-checkpoint-dir` and RL feature-window/action-space settings through paper runner overrides.

**Testing strategy:**
- Add parser/runner tests for the new algorithm and checkpoint-dir wiring.
- Add a shared-environment execution regression test proving `rl-capa-infer` reaches `evaluate_rl_capa` instead of training.
- Run a real smoke command using `outputs/plots/rl_capa_ablation_v2_500/rl-capa/checkpoints/` and verify metrics plus `summary.json`.
