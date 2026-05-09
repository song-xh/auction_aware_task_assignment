# RL-CAPA Inference Smoke Results

## Successful unified runner smoke

Command:

```bash
python3 runner.py run \
  --algorithm rl-capa-infer \
  --data-dir Data \
  --num-parcels 5 \
  --local-couriers 10 \
  --platforms 2 \
  --couriers-per-platform 5 \
  --task-window-start-seconds 0 \
  --task-window-end-seconds 30 \
  --partner-history-task-count-start 200 \
  --partner-history-task-count-step 0 \
  --rl-checkpoint-dir outputs/plots/rl_capa_ablation_v2_500/rl-capa/checkpoints \
  --rl-batch-actions 10 15 20 25 30 \
  --batch-size 30 \
  --step-seconds 60 \
  --episodes 1500 \
  --rl-discount-factor 1.0 \
  --rl-lr-actor 0.0002 \
  --rl-lr-critic 0.001 \
  --rl-entropy-start 0.05 \
  --rl-entropy-end 0.005 \
  --rl-entropy-decay-episodes 1000 \
  --rl-max-grad-norm 0.5 \
  --output-dir outputs/plots/rl_capa_infer_run_smoke_5
```

Observed metrics from `outputs/plots/rl_capa_infer_run_smoke_5/summary.json`:

- `TR = 36.144`
- `CR = 1.0`
- `BPT = 0.0006887309718877077`
- `delivered_parcels = 5`
- `accepted_assignments = 5`
- `timed_out_parcels = 0`

Artifacts written:

- `outputs/plots/rl_capa_infer_run_smoke_5/summary.json`
- `outputs/plots/rl_capa_infer_run_smoke_5/eval/summary.json`
- `outputs/plots/rl_capa_infer_run_smoke_5/eval/tr_over_batches.png`
- `outputs/plots/rl_capa_infer_run_smoke_5/eval/cr_over_batches.png`
- `outputs/plots/rl_capa_infer_run_smoke_5/eval/bpt_over_batches.png`

## Successful exp1 point-entry smoke

Command:

```bash
python3 experiments/run_chengdu_exp1_num_parcels.py \
  --execution-mode point \
  --point-value 5 \
  --output-dir outputs/plots/rl_capa_infer_exp1_point_smoke_5 \
  --algorithms rl-capa-infer \
  --data-dir Data \
  --num-parcels 500 \
  --local-couriers 10 \
  --platforms 2 \
  --couriers-per-platform 5 \
  --task-window-start-seconds 0 \
  --task-window-end-seconds 30 \
  --partner-history-task-count-start 200 \
  --partner-history-task-count-step 0 \
  --batch-size 30 \
  --rl-checkpoint-dir outputs/plots/rl_capa_ablation_v2_500/rl-capa/checkpoints \
  --rl-batch-actions 10 15 20 25 30 \
  --rl-step-seconds 60 \
  --rl-episodes 1500 \
  --rl-discount-factor 1.0 \
  --rl-lr-actor 0.0002 \
  --rl-lr-critic 0.001 \
  --rl-entropy-start 0.05 \
  --rl-entropy-end 0.005 \
  --rl-entropy-decay-episodes 1000 \
  --rl-max-grad-norm 0.5
```

Observed metrics from `outputs/plots/rl_capa_infer_exp1_point_smoke_5/rl-capa-infer/summary.json`:

- `TR = 14.928`
- `CR = 0.4`
- `BPT = 1.3835049922699513e-05`
- `delivered_parcels = 2`
- `accepted_assignments = 2`
- `timed_out_parcels = 0`

Artifacts written:

- `outputs/plots/rl_capa_infer_exp1_point_smoke_5/summary.json`
- `outputs/plots/rl_capa_infer_exp1_point_smoke_5/progress.json`
- `outputs/plots/rl_capa_infer_exp1_point_smoke_5/rl-capa-infer/summary.json`
- `outputs/plots/rl_capa_infer_exp1_point_smoke_5/rl-capa-infer/eval/summary.json`

## Longer comparison observations

Two heavier comparison attempts were started through the exp1 point entry:

- `outputs/plots/rl_capa_infer_point_smoke`
- `outputs/plots/rl_capa_infer_point_smoke_50`

In both cases, `capa` completed and wrote outputs, while `rl-capa-infer` did not finish within the observation window of this session. That indicates the shared-environment comparison path is wired, but realistic checkpoint inference at larger parcel counts remains materially slower than the unit smoke cases on the current CPU-only environment.
