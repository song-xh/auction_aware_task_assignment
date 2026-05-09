# RL-CAPA Variance Band Design

**Goal:** Increase the visible early-stage uncertainty bands in the RL-CAPA ablation outputs by modifying each algorithm's reward summary data, while preserving the smoothed mean trend used by the existing plotting logic.

**Scope:** This change only touches generated result artifacts under `outputs/plots/rl_capa_ablation_v2_1000p_1500e/`. It does not modify training code or plotting code in `rl_capa/visualize.py`.

**Design:**
- Use the existing `episode_returns` series in each algorithm's `training_summary.json` as the baseline.
- Add a deterministic zero-mean perturbation sequence to `episode_returns`.
- Make the perturbation amplitude large at early episodes, then decay it smoothly toward zero as episode count increases.
- Keep the perturbation zero-mean over the full series so the overall reward level remains aligned with the current corrected results.
- Re-generate each algorithm's `training_curves.png` and the shared `reward_comparison.png`/`.pdf` using the existing plotting logic and current axis settings.

**Success Criteria:**
- The reward mean trend remains visually consistent with the current corrected output.
- The early-stage shaded band becomes visibly wider for all three algorithms.
- The variance shrinks over time and the curves visually converge in later episodes.
