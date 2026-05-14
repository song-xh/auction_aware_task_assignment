#!/usr/bin/env bash
# Retrain RL-CAPA under domain randomization, addressing the diagnosis in
# docs/rl_capa_robust500_analysis.md:
#   - lower entropy bonus so pi2 logits actually move
#   - faster entropy decay (don't pin pi2 at uniform forever)
#   - more episodes to overcome DR-induced reward variance
#   - optional: narrower DR support (mild) for the first pass to confirm policies move
#
# Usage:
#   bash scripts/retrain_rl_capa_robust.sh A   # variant A: full DR + low entropy + 3000 ep
#   bash scripts/retrain_rl_capa_robust.sh B   # variant B: mild DR (delays<=20s, noise<=10%) + low entropy + 2000 ep
#   bash scripts/retrain_rl_capa_robust.sh C   # variant C: clean (no DR) sanity check, low entropy, 2000 ep
set -e

VARIANT=${1:-A}

COMMON=(
  --algorithm rl-capa
  --data-dir Data
  --num-parcels 500
  --local-couriers 10
  --platforms 2
  --couriers-per-platform 5
  --courier-capacity 50
  --service-radius-km 1.0
  --task-window-start-seconds 0
  --task-window-end-seconds 30
  --partner-history-task-count-start 200
  --partner-history-task-count-step 0
  --rl-batch-actions 10 15 20 25 30
  --step-seconds 60
  --rl-lr-actor 0.0003
  --rl-lr-critic 0.0005
  --rl-discount-factor 1.0
  --rl-max-grad-norm 0.5
  # KEY FIX 1: drop entropy ~10x so PG signal can move pi2 logits off zero
  --rl-entropy-start 0.005
  --rl-entropy-end 0.0005
)

case "$VARIANT" in
  A)  # full DR, longer schedule
    OUT=outputs/plots/rl_capa_robust_500_v2A_fullDR
    EXTRA=(
      --episodes 3000
      --rl-entropy-decay-episodes 1500
      --rl-domain-randomize
      --rl-domain-randomize-seed 0
    )
    ;;
  B)  # mild DR support: delays {0,5,10,15,20} sec, noise {-10..10}%
    OUT=outputs/plots/rl_capa_robust_500_v2B_mildDR
    EXTRA=(
      --episodes 2000
      --rl-entropy-decay-episodes 1000
      --rl-domain-randomize
      --rl-domain-randomize-seed 0
      --rl-domain-randomize-delays 0 5 10 15 20
      --rl-domain-randomize-noises -10 -5 0 5 10
    )
    ;;
  C)  # clean baseline (no DR) — sanity check that fix unlocks pi2 learning
    OUT=outputs/plots/rl_capa_robust_500_v2C_clean
    EXTRA=(
      --episodes 2000
      --rl-entropy-decay-episodes 1000
    )
    ;;
  *)
    echo "Unknown variant: $VARIANT"; exit 1
    ;;
esac

mkdir -p "$OUT"
echo "[retrain] variant=$VARIANT  output=$OUT"

python3 runner.py run "${COMMON[@]}" "${EXTRA[@]}" --output-dir "$OUT" 2>&1 | tee "$OUT/train.log"

echo "[retrain] DONE -> $OUT"
echo "[retrain] checkpoint at $OUT/checkpoints/"
echo
echo "Quick health check (entropy_pi2 should drop below 0.6 after ~200 ep):"
python3 - <<EOF
import json, statistics
d = json.load(open("$OUT/training_summary.json"))
def s(k, idx): return d[k][idx] if idx < len(d[k]) else None
n = len(d["episode_returns"])
checkpoints = [0, min(100, n-1), min(500, n-1), min(1000, n-1), n-1]
print(f"{'episode':>8s} {'return':>10s} {'ent_pi1':>9s} {'ent_pi2':>9s} {'mean_bs':>8s}")
for i in checkpoints:
    print(f"{i:>8d} {s('episode_returns', i):>10.1f} "
          f"{s('entropy_pi1', i):>9.4f} {s('entropy_pi2', i):>9.4f} "
          f"{s('mean_batch_size', i):>8.2f}")
ret_first = statistics.mean(d["episode_returns"][:50])
ret_last  = statistics.mean(d["episode_returns"][-50:])
print(f"\nReturn improvement: {ret_first:.1f} -> {ret_last:.1f} ({100*(ret_last-ret_first)/ret_first:+.1f} %)")
EOF
