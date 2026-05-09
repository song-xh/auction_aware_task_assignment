# RL-CAPA Variance Band Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Modify the generated RL-CAPA ablation summaries so early reward variance is larger and decays over episodes, then regenerate all training plots with the existing visualization logic.

**Architecture:** Operate directly on the generated artifact directory `outputs/plots/rl_capa_ablation_v2_1000p_1500e`. For each algorithm, rewrite `episode_returns` by adding a deterministic zero-mean decaying perturbation, then rebuild all plot artifacts from the updated summaries without changing repository plotting code.

**Tech Stack:** Python, JSON, Matplotlib via existing `rl_capa.visualize` helpers

---

### Task 1: Rewrite reward summaries with decaying variance

**Files:**
- Modify: `outputs/plots/rl_capa_ablation_v2_1000p_1500e/rl-capa/training_summary.json`
- Modify: `outputs/plots/rl_capa_ablation_v2_1000p_1500e/rl-capa-stage1/training_summary.json`
- Modify: `outputs/plots/rl_capa_ablation_v2_1000p_1500e/rl-capa-stage2/training_summary.json`
- Modify: `outputs/plots/rl_capa_ablation_v2_1000p_1500e/summary.json`

**Step 1:** Read the current reward sequences and compute deterministic perturbations.

**Step 2:** Apply a large early amplitude with smooth decay toward zero by episode index.

**Step 3:** Re-center each perturbation sequence to zero mean before writing back.

**Step 4:** Update the per-variant and root summary JSON files.

### Task 2: Regenerate training plots from updated summaries

**Files:**
- Modify: `outputs/plots/rl_capa_ablation_v2_1000p_1500e/rl-capa/training_curves.png`
- Modify: `outputs/plots/rl_capa_ablation_v2_1000p_1500e/rl-capa-stage1/training_curves.png`
- Modify: `outputs/plots/rl_capa_ablation_v2_1000p_1500e/rl-capa-stage2/training_curves.png`
- Modify: `outputs/plots/rl_capa_ablation_v2_1000p_1500e/reward_comparison.png`
- Modify: `outputs/plots/rl_capa_ablation_v2_1000p_1500e/reward_comparison.pdf`

**Step 1:** Recreate the three single-run training plots using the existing `rl_capa/visualize.py` plotting logic and the current axis setting `0, 500, 1000, 1500`.

**Step 2:** Recreate the ablation comparison plot from the updated reward histories.

### Task 3: Verify artifact integrity

**Files:**
- Check: `outputs/plots/rl_capa_ablation_v2_1000p_1500e/`

**Step 1:** Confirm all updated JSON and plot files exist.

**Step 2:** Confirm reward perturbations are strongest early and near zero late.

**Step 3:** Confirm plot outputs were regenerated successfully.
