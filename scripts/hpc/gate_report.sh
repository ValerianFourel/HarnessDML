#!/bin/bash
# Read the difficulty gate (§4.4) for a model whose pilot has finished:
# aggregate its pilot slices and print BARE / T accuracy per band with the
# IN / OUT verdict against the [0.15, 0.85] window. Login node.
#
#   bash scripts/hpc/gate_report.sh qwen_3_5_122b
#
# Then record the ruling in configs/gates.yaml (status: census | thin |
# dropped) and submit the chains for the bands that came back IN. Nothing
# here submits anything.
set -uo pipefail
cd "$(dirname "$0")/../.."
source scripts/hpc/env.sh
MODEL=${1:?usage: gate_report.sh <model_id>}
LO=0.15; HI=0.85

found=0
printf "\n%-10s %8s %8s   %s\n" "band" "BARE" "T" "verdict"
printf -- "----------------------------------------------------\n"
for d in "$SCRATCH"/harnesslab/pilot/rollouts_"${MODEL}"_*; do
  [ -f "$d/rollouts.jsonl" ] || continue
  found=1
  bench=$(basename "$d"); bench=${bench##*_}
  out="results/pilot_${MODEL}_${bench}"
  python -m harnesslab.cli aggregate --rollouts "$d" --out "$out" >/dev/null 2>&1 || {
    printf "%-10s %8s %8s   AGGREGATE FAILED (run it by hand to see why)\n" "$bench" "-" "-"
    continue; }
  # REPORT.md: | config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
  read -r bare t < <(awk -F'|' -v OFS=' ' '
    $2 ~ /^ *BARE *$/ {b=$5+0}
    $2 ~ /^ *T *$/    {t=$5+0}
    END {printf "%.3f %.3f", b, t}' "$out/REPORT.md")
  # ADR 18's ruling order: saturation is decided by BARE alone (mistral x
  # gsm8k went thin on BARE .875 even though T .60 sat mid-window), then a
  # band enters if EITHER arm is inside, then the floor drops it.
  # awk has no line continuation inside a parenthesised expression — keep each
  # print on one line (a wrapped ternary is a syntax error, not a style issue).
  # SE ~ .055 at n=20x2, so a BARE just under the floor is noise, not a floor.
  verdict=$(awk -v b="$bare" -v t="$t" -v lo=$LO -v hi=$HI 'BEGIN{
    if (b > hi) { print "OUT (BARE saturates) -> status: thin"; exit }
    if ((b>=lo && b<=hi) || (t>=lo && t<=hi)) {
      if (b < lo) { print "IN (floor-marginal BARE — flag) -> status: census"; exit }
      if (b > hi-0.05 || t > hi) { print "IN (near ceiling — flag) -> status: census"; exit }
      print "IN  -> status: census"; exit }
    print "OUT (floor) -> status: dropped" }')
  printf "%-10s %8s %8s   %s\n" "$bench" "$bare" "$t" "$verdict"
done
[ "$found" = 1 ] || { echo "no pilot stores for $MODEL under \$SCRATCH/harnesslab/pilot"; exit 1; }

cat <<EOF

Window [$LO, $HI] on BARE/T accuracy (§4.4). A band enters the census if
EITHER arm lands inside it. Record the ruling in configs/gates.yaml, then:

  EXP=configs/experiments/mvp_grid.yaml MODEL_ID=$MODEL BENCH=<band> \\
    sbatch --job-name "hl-$MODEL-<band>" slurm/run_experiment.sbatch

(chain the links with --dependency=afterany — see scripts/hpc/submit_census_wave2.sh)
EOF
