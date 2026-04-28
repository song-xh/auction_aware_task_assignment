# Deadline Disturbance Experiments Design

## Goal

Add two reviewer-response experiments that compare `rl-capa` and `ramcom` under deadline disturbance while preserving the original Chengdu task `d_time` as the true deadline.

## Scope

This change adds:

- `Exp-7`: processing-delay disturbance with delay values `5, 10, 15, 20, 30, 60` seconds.
- `Exp-8`: perceived-deadline noise with ratio values `-20, -15, -10, -5, 0, 5, 10, 15, 20` percent.
- CLI scripts, split/direct execution, progress reporting, aggregate summaries, and plots aligned with the existing Chengdu experiment framework.

Both experiments default to `rl-capa ramcom`. `rl-capa` is retrained from scratch at every disturbance point.

## Deadline Semantics

The original task field `d_time` remains the true deadline and must not be overwritten.

For model-facing disturbance, cloned tasks receive temporary fields:

- `observed_s_time`: the model-facing release time used by Exp-7 processing delay.
- `observed_d_time`: the model-facing deadline used by Exp-8 deadline noise.

The environment and algorithms read the temporary fields only when explicitly configured for these experiments. True expiration and final validity accounting continue to use `d_time`, so positive deadline noise can cause the model to believe a task is still available after the true deadline has passed.

## Exp-7: Processing Delay

For a delay value `delta`, the experiment derives the point environment by setting:

```text
observed_s_time = s_time + delta
d_time = original d_time
```

Batch collection uses `observed_s_time` when the disturbance field exists. This means the parcel becomes visible to the algorithm later while its true deadline is unchanged, reducing available slack by `delta`.

Expected trend:

- Larger `delta` decreases `TR` for both algorithms.
- `rl-capa` should lose less `TR` than `ramcom` because it can learn delay-aware batch and cross-platform decisions at each disturbance level.

## Exp-8: Deadline Noise

For a ratio value `rho`, the experiment derives the point environment by setting:

```text
slack = max(0, d_time - s_time)
observed_d_time = d_time + round(slack * rho / 100)
d_time = original d_time
```

The use of slack rather than absolute `d_time` keeps the noise proportional to each task's decision window. Positive values mean the model perceives a later deadline; negative values mean it perceives an earlier deadline.

Expected trend:

- Larger positive noise should reduce `TR` more strongly because decisions may wait past the true deadline.
- Negative noise can reduce revenue by forcing earlier decisions, but should usually be less destructive than positive noise.
- `rl-capa` should lose less `TR` than `ramcom` when retrained per noise level.

## Architecture

Add a small disturbance layer instead of duplicating algorithms:

- `experiments/deadline_disturbance.py`: task-field helpers, point-environment derivation, and summary axis metadata.
- `env/chengdu.py`: central accessors for observed release/deadline fields, used by sorting, batch collection, model-facing parcel conversion, and true-expiry checks.
- `baselines/common.py`, `baselines/ramcom.py`, and RL-CAPA environment paths: use the shared model-facing conversion/accessors rather than directly reading `d_time` for decisions.
- `experiments/paper_chengdu.py`: register new axes, labels, canonical seeds, plotting metadata, and runner overrides.
- `experiments/run_chengdu_exp7_deadline_delay.py` and `experiments/run_chengdu_exp8_deadline_noise.py`: paper-style CLI wrappers.

The true-deadline rule should remain explicit: expiration and final accepted-revenue validity use `d_time`; model-facing state and feasibility use the observed field when present.

## CLI Shape

Formal examples:

```bash
python3 experiments/run_chengdu_exp7_deadline_delay.py \
  --execution-mode split \
  --tmp-root /tmp/exp7_deadline_delay \
  --output-dir outputs/plots/exp7_deadline_delay \
  --preset formal \
  --algorithms rl-capa ramcom \
  --data-dir Data
```

```bash
python3 experiments/run_chengdu_exp8_deadline_noise.py \
  --execution-mode split \
  --tmp-root /tmp/exp8_deadline_noise \
  --output-dir outputs/plots/exp8_deadline_noise \
  --preset formal \
  --algorithms rl-capa ramcom \
  --data-dir Data
```

Both scripts keep existing fixed-parameter flags from `build_script_parser`, including RL training overrides if already supported by the shared parser after implementation.

## Outputs

Each experiment writes:

- Per-point `summary.json`.
- Per-algorithm subdirectories with existing algorithm outputs.
- Aggregate `summary.json`.
- `paper_manifest.json`.
- `tr_vs_deadline_delay.png` for Exp-7.
- `tr_vs_deadline_noise.png` for Exp-8.

The aggregate summary includes `TR`, `CR`, and `BPT` for each algorithm at each disturbance point, even though the response narrative focuses on local-platform `TR`.

## Testing

Add focused tests before implementation:

- Disturbance helpers do not overwrite `d_time`.
- Exp-7 uses delayed observed release time while preserving true deadline.
- Exp-8 computes positive and negative observed deadlines from slack.
- Batch visibility uses `observed_s_time` when present.
- Model-facing parcel conversion uses `observed_d_time` when present.
- True expiry still uses `d_time`.
- Exp-7 and Exp-8 smoke CLIs produce aggregate summaries and plot paths for tiny input settings.

## Commits

After design approval:

1. Commit this design document.
2. Write and commit an implementation plan.
3. Implement and verify Exp-7, then commit.
4. Implement and verify Exp-8, then commit.
