#!/bin/bash
# Cross-model view of what the harness DID: headline-config accuracy for every
# (model, band) that has a committed panel. Reads results/ only — no cluster,
# no $SCRATCH, runs anywhere the repo is checked out.
#
#   bash analysis/model_matrix.sh            # pilots (all models, N=20x2)
#   bash analysis/model_matrix.sh mvp_grid   # census slices instead
#   bash analysis/model_matrix.sh ''         # every experiment in results/
#
# Columns are the four headline configs (§4.6): BARE, T, T+SR+R, All-In. This
# is descriptive only — cell means with no inference, no ranking, and no
# cross-model claim beyond "these are the numbers on the committed lists"
# (§5 generalization scope: model and band are fixed factors).
set -uo pipefail
cd "$(dirname "$0")/.."
PREFIX=${1-pilot}

printf "%-34s %8s %8s %8s %8s\n" "slice" "BARE" "T" "T+SR+R" "All-In"
printf -- "------------------------------------------------------------------------\n"
found=0
for f in results/"$PREFIX"*/REPORT.md; do
  [ -f "$f" ] || continue
  found=1
  s=${f#results/}; s=${s%/REPORT.md}
  # REPORT.md: | config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
  awk -F'|' -v s="$s" '
    $2 ~ /^ *BARE *$/          {b=$5+0}
    $2 ~ /^ *T *$/             {t=$5+0}
    $2 ~ /^ *T\+SR\+R *$/      {r=$5+0}
    $2 ~ /^ *P\+T\+M\+SR\+R *$/{a=$5+0}
    END {printf "%-34.34s %8.3f %8.3f %8.3f %8.3f\n", s, b, t, r, a}' "$f"
done | sort
[ "$found" = 1 ] || { echo "no results/${PREFIX}*/REPORT.md — harvest first"; exit 1; }

cat <<'EOF'

y_mean per cell (token-F1 on QA, EM on math). Gate window is [0.15, 0.85] on
BARE/T; a band outside it on both is dropped or thinned (configs/gates.yaml).
EOF
