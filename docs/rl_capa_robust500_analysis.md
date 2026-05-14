# RL-CAPA Robust-500 Training Diagnosis

Training run: `outputs/plots/rl_capa_robust_500/` (1500 episodes, domain randomization on, 500 parcels).

## TL;DR

- **Reward non-convergence is partly expected DR phenomenon, partly a design weakness — not a code bug.**
- π1 collapses to the smallest batch action (always 10) by ~episode 500.
- π2 *never moves from uniform* (per-parcel cross probability ≈ 0.5 throughout, entropy stuck at ln 2 ≈ 0.693).
- "Loss converged" is misleading: the small loss values reflect (a) deterministic π1 ⇒ log_prob_1 → 0, (b) V2 fitting per-step reward ⇒ |adv_2| → 0. They do **not** indicate policy improvement.
- Reward is structurally lower than the no-DR run because the average over `(delay, noise)` includes harsh disturbances that cause timeouts.

## Direct Evidence

### Training summary (`training_summary.json`)

| Metric | ep 0 | ep 100 | ep 500 | ep 1000 | ep 1499 |
|---|---|---|---|---|---|
| episode_returns | 2094 | — | — | — | 2046 |
| mean_batch_size | 21.0 | 19.8 | — | — | 10.0 |
| entropy_pi1 | 1.608 | 0.596 | 0.0008 | 0.0003 | 6.1e-6 |
| entropy_pi2 | 0.689 | 0.693 | 0.693 | 0.692 | 0.690 |
| loss_pi1 | -0.095 | -0.892 | 1e-4 | 2.8e-5 | 8.5e-7 |
| loss_v1 | 549 665 | 656 851 | 39 738 | 5 449 | 2 426 |

Returns first 50 ep mean = 2053 (std 100). Returns last 50 ep mean = 2046 (std 94). **Identical mean and variance — no learning signal in the reward.**

### Disturbance sampler is functioning

63 unique `(delay, noise)` pairs across 1500 episodes (delays in {0, 5, 10, 15, 20, 30, 60} s; noise in {-20…+20} %). Per-episode randomization works correctly.

### Loaded checkpoint probe

```
pi2 logits: mean = -0.03,  std = 0.11
pi2 cross prob: mean = 0.49,  range [0.43, 0.53]
pi2 entropy per state: 0.692       ← Bernoulli max entropy = ln 2 = 0.693
pi1 prob[batch=10] = 1.0  on every state
```

π2 is at initialization. π1 is fully deterministic on `batch=10`.

## Mechanism

### Why π1 collapses to the smallest batch under DR

`Q1` is action-conditional and trained on episode discounted returns `R̂_t`.
With DR, `R̂_t` has huge variance from disturbances *not visible* in `s_t^(1)`.
`loss_v1` shrinks from 5.5e5 → 2.4e3, but a residual std ≈ √2400 ≈ 49 still dominates the per-action delta in `Q1`.
The smallest batch action (`batch=10`) finishes faster, exposing fewer parcels to extreme deadline disturbances ⇒ Q1 marginally prefers it.
Because `A1 = Q1(s,a) − E_{a'∼π1}[Q1(s,a')]` is action-conditional and *non-zero even when π1 is deterministic* (counterfactual baseline), the gradient keeps pushing π1 toward the slightly-higher-Q action until the policy delta-function is reached. This matches the design (`docs/review_0507.md §3.2`).

### Why π2 never moves from uniform

`A2 = r_t − V2(s2_agg)`, and `V2` is trained to regress `r_t`. As `loss_v2` falls (126 → 56), `|A2|` ≈ residual noise of `r_t − E[r_t|state]`. Two consequences:

1. The policy-gradient term `−log_prob_2 · A2` has near-zero mean signal under DR (the disturbance-induced residual is unconditioned noise, uncorrelated with the per-parcel action).
2. The entropy bonus `−ent_coeff · H(π2)` actively pulls each Bernoulli logit toward 0 (uniform). With `ent_coeff ∈ [0.005, 0.05]` (per the training command), this term dominates the noisy gradient, locking each logit at ~0.

Result: π2 logits stay at ≈ 0 ⇒ entropy stays at ln 2 ⇒ reward never reflects any cross-or-not learning.

### Why the losses look "converged"

| Loss | Final value | Why it shrunk |
|---|---|---|
| `loss_pi1` | ~1e-6 | `π1` deterministic ⇒ `log_prob_1 = log 1 = 0` ⇒ `−log_prob·adv → 0`. Trivial, not learning. |
| `loss_pi2` | ~2 | `|adv_2|` shrinks as `V2` fits per-step reward; entropy term still small. |
| `loss_v1` | ~2.4e3 | V1 explains state-mean only; residual = irreducible disturbance noise. |
| `loss_v2` | ~56 | V2 explains per-step reward up to disturbance noise. |

Conclusion: the small actor losses are an **artifact** of `log_prob → 0` and `|adv| → 0`, not a sign of improving policy.

### Why reward is far below the no-DR baseline

Reference: `result/rl_capa_run/training_summary.json` (no DR, 5000 ep) ⇒ returns 2415 → 3516 (clear monotone improvement).

Robust-500 returns hover at ~2050. That is ~58 % of the clean asymptote. Two contributors:

1. **Structural penalty.** Some sampled `(delay=60, noise=±20)` episodes lose many parcels to perceived-deadline timeouts ⇒ the *expected* reward over the disturbance distribution is lower than the clean reward.
2. **Policy stuck near init.** π2 uniform random + π1 fixed at `batch=10` ⇒ no learning gain on top of the random baseline.

## Classification

- **Code bug?** No. Gradient flow is correct, advantages are correctly normalized (mean-centered + std-scaled with collapse-safe fallback), DR sampling is correct, V2 input includes the `Δ_b` (a₁) component as required by spec, state features include drift signals (`recent_timeout_ratio`, `recent_unresolved_ratio`).
- **Expected DR phenomenon?** Partly. Mean reward dropping is correct robust-RL behavior. But π2 frozen at uniform is *too pathological* to be acceptable.
- **Design weakness?** Yes. Specifically:
  1. Entropy bonus on π2 (start 0.05) is too high relative to A2 magnitude under DR. With `0.005 ≤ ent_coeff ≤ 0.05` and `|A2|` shrinking toward noise, the entropy term pins π2 to uniform.
  2. 1500 episodes is too few to overcome DR variance — the no-DR baseline needed 5000 ep just to converge without any disturbance noise to fight.
  3. State features do *not* expose the actual disturbance level to the critics, so V1/V2 cannot disentangle "policy quality" from "this episode's disturbance" ⇒ noisy advantage ⇒ slow / no learning.

## Recommendations (no code change yet — pending eval results)

1. **Reduce π2 entropy bonus** — try `entropy_start=0.005, entropy_end=0.0005` so policy-gradient signal can move logits.
2. **Curriculum DR** — train clean for the first ~500 ep (let π1/π2 reach a useful operating point), then ramp DR severity.
3. **Increase episodes** — at minimum 3000–5000 with DR, given the no-DR baseline already needed 5000.
4. **Optionally expose disturbance level to critics during training** (oracle critic). The actor never sees it, so it remains test-time-deployable.

## Empirical Robustness Check (pending)

Eval on Exp-7 (delay axis: 5, 10, 15, 20, 30, 60 s) and Exp-8 (noise axis: −20…+20 %) using the trained ckpt vs `ramcom`. Result table to be appended after sequential run completes (see `outputs/plots/rl_capa_robust_500/eval/`).

If trained RL-CAPA ≲ `ramcom` across all axis points → confirms the policy did not learn anything useful under DR (consistent with the π2-frozen / π1-collapsed observations above) and the recommendations above are the way forward.
