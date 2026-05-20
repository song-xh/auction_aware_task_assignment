# Exp2 BPT And Baseline Tuning Design

**Context**

`result/exp2_ny_couriers_d600/summary.json` currently shows two distinct problems:

1. `BPT` is measured under different contracts.
   - `capa` reports widened batch runtime (`processing_time_seconds` plus batch movement overhead).
   - `greedy`, `basegta`, `impgta`, `ramcom`, and `mra` still report decision-only mean time with routing, insertion, and movement excluded.
   - This makes `capa` look artificially expensive while several baselines are near zero.

2. `greedy` and `mra` have low `CR` under the current NY Exp-2 setting.
   - `greedy` is a realtime `local-only` baseline and never uses cross-platform supply.
   - `mra` is a batched `local-only` baseline; deadline loss is amplified by waiting until batch end before matching.
   - Under `deadline_seconds=600` and `service_radius_km=1.0`, both methods are capacity- and reachability-limited by design.

**Goals**

1. Expand baseline `BPT` so it covers matching-runtime work that users expect:
   - feasible-courier search
   - route insertion search
   - graph / bid construction
   - auction / matching selection

2. Keep algorithm identities intact.
   - `greedy` remains `local-only greedy`
   - `mra` remains `local-only multi-round batch matching`
   - no hidden cross-platform fallback is added

3. Raise `greedy` and `mra` `CR` by retuning the fixed Exp-2 environment rather than rewriting the baselines into different algorithms.

4. Preserve the qualitative ordering target:
   - `capa` stays best on `TR` / `CR`
   - `ramcom > mra > greedy` on `TR`
   - baseline `CR` values are no longer abnormally low
   - `BPT` grows with courier count and is no longer close to zero for most baselines

**Decisions**

1. Redefine baseline `BPT` as full matching-epoch elapsed runtime.
   - For `greedy`, `basegta`, `impgta`, and `ramcom`, one epoch is one task-arrival decision.
   - For `mra`, one epoch is one multi-round batch-matching round.
   - This includes routing and insertion work because those are part of the assignment algorithm cost.
   - Route-drain / movement between epochs stays excluded from baseline `BPT`, because the user request is specifically about matching work rather than simulator progression.

2. Keep CAPA on the existing widened batch-runtime contract.
   - CAPA already reports per-batch wall-clock matching time plus the batch movement overhead tracked outside the matching window.
   - The change is therefore to expand baseline accounting upward, not to shrink CAPA downward.

3. Fix revenue-parameter propagation at the paper-runner layer.
   - Baseline runners already accept `local_payment_ratio_zeta` and `cross_platform_sharing_rate_mu2`.
   - `build_paper_runner_overrides_from_fixed_config()` must also forward these parameters, not only prediction controls.
   - This makes formal/split paper runs tunable and fair across algorithms.

4. Tune Exp-2 with environment parameters first, algorithm parameters second.
   - Primary knobs for `CR`: `deadline_seconds`, `service_radius_km`, `batch_size`
   - Primary knobs for `TR` ordering: `local_payment_ratio_zeta`, `cross_platform_sharing_rate_mu2`, `prediction_window_seconds`, `prediction_success_rate`

**Initial Tuning Envelope**

- `deadline_seconds`: `600 -> {720, 900}`
- `service_radius_km`: `1.0 -> {1.2, 1.5}`
- `batch_size`: `30 -> {20, 15}` to reduce MRA deadline loss
- `prediction_window_seconds`: `{30, 60, 90}`
- `prediction_success_rate`: `{0.6, 0.7, 0.8}`
- `local_payment_ratio_zeta`: `{0.4, 0.5}`
- `cross_platform_sharing_rate_mu2`: `{0.2, 0.25, 0.3}`

**Non-Goals**

- No new fallback logic
- No algorithm-family changes
- No silent curve editing in result summaries
- No manual post-processing of metrics outside the runner code
