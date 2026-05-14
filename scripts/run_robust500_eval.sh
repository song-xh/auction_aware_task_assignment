#!/usr/bin/env bash
# Sequential exp7/exp8 eval for rl_capa_robust_500 ckpt vs ramcom.
set -e
CKPT=outputs/plots/rl_capa_robust_500/checkpoints
ROOT=outputs/plots/rl_capa_robust_500/eval

COMMON=(
  --algorithms rl-capa-infer ramcom
  --rl-checkpoint-dir "$CKPT"
  --num-parcels 500 --local-couriers 10 --platforms 2 --couriers-per-platform 5
  --courier-capacity 50 --service-radius-km 1.0
  --task-window-start-seconds 0 --task-window-end-seconds 30
  --partner-history-task-count-start 200 --partner-history-task-count-step 0
  --rl-batch-actions 10 15 20 25 30 --rl-step-seconds 60
)

run_point () {
  local script=$1
  local axis_label=$2
  local v=$3
  local out=$ROOT/$axis_label
  mkdir -p "$out"
  local token
  token=$(echo "$v" | sed 's/-/m/; s/\./_/')
  local pdir=$out/point_$token
  mkdir -p "$pdir"
  echo "[$axis_label] point=$v -> $pdir"
  python -m "$script" \
    --execution-mode point "--point-value=$v" \
    --output-dir "$pdir" \
    "${COMMON[@]}" 2>&1 | tail -3
}

for v in 5 10 15 20 30 60; do
  run_point experiments.run_chengdu_exp7_deadline_delay exp7 "$v"
done

for v in -20 -15 -10 -5 0 5 10 15 20; do
  run_point experiments.run_chengdu_exp8_deadline_noise exp8 "$v"
done

echo DONE
