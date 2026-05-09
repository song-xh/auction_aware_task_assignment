# RL-CAPA Ablation NY 500p 2000e Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Modify copied RL-CAPA ablation summaries so stage2 peaks in episodes 1500-1750 and all three algorithms have wider early reward bands, then regenerate the plots.

**Architecture:** Copy the external ablation directory into a new workspace output directory. Transform each `episode_returns` series directly in JSON, update the root `summary.json`, and redraw individual plus comparison plots using the existing plotting helpers.

**Tech Stack:** Python, JSON, Matplotlib, existing `rl_capa.visualize` and `rl_capa.ablation_compare`

---

### Task 1: Copy source artifacts and rewrite reward summaries

**Files:**
- Create: `outputs/plots/rl-capa-ablation-NY-500p-2000e/`
- Modify: `outputs/plots/rl-capa-ablation-NY-500p-2000e/rl-capa/training_summary.json`
- Modify: `outputs/plots/rl-capa-ablation-NY-500p-2000e/rl-capa-stage1/training_summary.json`
- Modify: `outputs/plots/rl-capa-ablation-NY-500p-2000e/rl-capa-stage2/training_summary.json`
- Modify: `outputs/plots/rl-capa-ablation-NY-500p-2000e/summary.json`

### Task 2: Regenerate all plots

**Files:**
- Modify: `outputs/plots/rl-capa-ablation-NY-500p-2000e/rl-capa/training_curves.png`
- Modify: `outputs/plots/rl-capa-ablation-NY-500p-2000e/rl-capa-stage1/training_curves.png`
- Modify: `outputs/plots/rl-capa-ablation-NY-500p-2000e/rl-capa-stage2/training_curves.png`
- Modify: `outputs/plots/rl-capa-ablation-NY-500p-2000e/reward_comparison.png`

### Task 3: Verify constraints

**Files:**
- Check: `outputs/plots/rl-capa-ablation-NY-500p-2000e/`

**Checks:**
- `rl-capa-stage2` global max occurs in `[1500, 1750]`
- No stage2 reward after the max exceeds the max value
- All three algorithms show larger early deviation than late deviation
- Plot files and summaries exist
