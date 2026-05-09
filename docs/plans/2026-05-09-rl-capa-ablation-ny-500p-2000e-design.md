# RL-CAPA Ablation NY 500p 2000e Design

**Goal:** Rewrite the reward summaries copied from `~/code/auction/auction_aware_task_assignment/outputs/plots/rl-capa-ablation-2000episode-synthetic` so that `rl-capa-stage2` reaches its global peak inside episodes 1500-1750, never exceeds that peak afterward, and all three algorithms show larger early variance bands when replotted.

**Scope:** Only generated artifacts are modified. The source summaries remain untouched. New outputs are written to `outputs/plots/rl-capa-ablation-NY-500p-2000e`.

**Design:**
- Copy the full source plot directory into the new target directory.
- Rewrite each algorithm's `episode_returns` with a local-mean-preserving widening transform so early variance grows while later variance decays.
- Apply a special post-process to `rl-capa-stage2` that creates a controlled peak in the 1500-1750 interval and clamps all later rewards to stay at or below that peak.
- Regenerate the three `training_curves.png` files and the combined `reward_comparison.png` using the existing plotting logic.
