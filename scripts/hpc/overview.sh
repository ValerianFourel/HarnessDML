#!/bin/bash
# Full-view snapshot of the whole experiment on JUPITER: code version, quotas,
# jobs now, outcomes, every rollout store with census progress, server health,
# harvested results, probe/pilot verdicts, venv integrity.  Login node.
#
#   bash scripts/hpc/overview.sh          # snapshot
#   RATE=1 bash scripts/hpc/overview.sh   # + measure throughput over 60 s
#
# Read-only; safe to run anytime, including mid-census. status.sh is the fast
# pulse (jobs + stores); this is the "what is the state of everything" report.
set -uo pipefail
cd "$(dirname "$0")/../.." || exit 1
source scripts/hpc/env.sh
hr(){ printf '\n\033[1m===== %s =====\033[0m\n' "$1"; }

hr "0. WHERE / WHEN / CODE VERSION"
date; echo "host=$(hostname)  user=$USER  repo=$PWD"
echo "SCRATCH=${SCRATCH:-<unset!>}"
git log --oneline -3
echo "-- local modifications on this clone (normally empty):"
git status --porcelain | head -10
grep -m1 "n_tasks" configs/experiments/mvp_grid.yaml

hr "1. QUOTAS  (a full \$HOME silently kills EVERY job at startup)"
du -sh "$HOME/.cache" 2>/dev/null
[ -n "${SCRATCH:-}" ] && du -sh "$SCRATCH/harnesslab" 2>/dev/null
jutil user projects 2>/dev/null | head -3

hr "2. JOBS RIGHT NOW"
printf "running=%s  pending=%s\n" \
  "$(squeue -u "$USER" -h -t R | wc -l)" "$(squeue -u "$USER" -h -t PD | wc -l)"
squeue -u "$USER" -o "%.11i %.9T %.34j %.9M %.10L %.5D %R" | head -60

hr "3. PENDING: why  ((Dependency) = healthy resume chain)"
squeue -u "$USER" -h -t PD -o "%R" | sort | uniq -c | sort -rn

hr "4. OUTCOMES — last 24 h"
sacct -u "$USER" --starttime now-24hours -X -n -o State%14 2>/dev/null \
  | awk '{print $1}' | sort | uniq -c | sort -rn
echo "-- anything not COMPLETED/RUNNING/PENDING:"
sacct -u "$USER" --starttime now-24hours -X -n -o JobID%12,JobName%30,State%12,Elapsed%10,ExitCode 2>/dev/null \
  | grep -vE "COMPLETED|RUNNING|PENDING" | head -20
echo "   (exit 3 = api-error/stay-pending resume path; exit 4 = serve never got"
echo "    healthy by the ceiling — check the venv, §10)"

hr "5. WHAT IS DONE — every rollout store, census progress, live?"
# census target per bench = n_tasks x 32 configs x 5 seeds  (mvp_grid.yaml)
target_for(){ case "$1" in
  hotpotqa) echo 480000;; musique) echo 386720;; gsm8k) echo 211040;; math) echo 41920;;
  *) echo 0;; esac; }
tot=0; lines=""; permodel=""
for d in "$SCRATCH"/harnesslab/*/rollouts_*; do
  f="$d/rollouts.jsonl"; [ -f "$f" ] || continue
  n=$(wc -l < "$f")
  rel=${d#"$SCRATCH"/harnesslab/}; exp=${rel%%/*}; slice=${rel#*/rollouts_}
  bench=${slice##*_}; model=${slice%_*}
  live="    "; [ -n "$(find "$f" -mmin -10 2>/dev/null)" ] && live="LIVE"
  pct="   -"   # non-census stores (pilot, arms, smoke) have no census target
  case "$exp" in
    mvp_grid|mvp_thin*)
      tot=$((tot + n))
      permodel+="$n $model"$'\n'
      t=$(target_for "$bench"); [ "$t" -gt 0 ] && pct=$(printf "%3d%%" $(( 100 * n / t )))
      ;;
  esac
  # NOTE: accumulate, print AFTER the loop — piping the loop into sort would
  # run it in a subshell and reset the counters (the af73fa9 bug).
  lines+="$(printf "%10d %s %s  %s" "$n" "$pct" "$live" "$rel")"$'\n'
done
printf "%s" "$lines" | sort -rn | sed 's/^/  /'
echo "  ------------------------------------------------------"
printf "  CENSUS TOTAL (mvp_grid + mvp_thin): %d\n" "$tot"

hr "6. CENSUS BY MODEL"
printf "%s" "$permodel" | awk 'NF{s[$2]+=$1} END{for(m in s) printf "%10d  %s\n", s[m], m}' | sort -rn

hr "7. RUNNING SERVERS: healthy? producing? real errors?"
# grep for the ABI break by its exact message — a transformers deprecation
# warning contains the bare word "torchvision" and would false-positive.
for j in $(squeue -u "$USER" -h -t R -o %i); do
  echo "--- job $j ---"
  grep -hE "\[serve\]|healthy|\[run\]" "slurm-$j.out" 2>/dev/null | tail -3
  log="$SCRATCH/harnesslab/serverlogs/${j}_8001.log"
  if [ -f "$log" ]; then
    grep -m2 -E "torchvision::nms does not exist|_vllm_fa[23]_C|illegal memory|Disk quota|CUDA error|^ValueError|^RuntimeError" \
      "$log" | sed 's/^/   REAL-ERR> /'
    echo "   last server line: $(tail -1 "$log" | cut -c1-120)"
  fi
done

hr "8. HARVESTED / COMMITTED RESULTS (in git)"
ls -1 results/ 2>/dev/null | sed 's/^/  /'
echo "-- recent results commits:"
git log --oneline -8 -- results/ | sed 's/^/  /'

hr "9. PROBE + PILOT VERDICTS — last 24 h"
sacct -u "$USER" --starttime now-24hours -X -n -o JobID%12,JobName%34,State%12 2>/dev/null \
  | grep -Ei "probe|pilot" | while read -r jid jname jstate; do
  v=$(grep -hoE "Action: [A-Za-z]+\[|Answer:|FATAL|healthy|ValueError:" "slurm-${jid}.out" 2>/dev/null \
      | sort -u | tr '\n' ' ')
  y=$(grep -hoE "y=[0-9.]+" "slurm-${jid}.out" 2>/dev/null | tail -4 | tr '\n' ' ')
  printf "  %-12s %-34s %-11s :: %s %s\n" "$jid" "$jname" "$jstate" "${v:-<no verdict>}" "$y"
done

hr "10. VENV INTEGRITY (serve path, not just 'import vllm')"
# flash-attn loads lazily at `vllm serve`, so a bare import passes even when
# the compiled stack is ABI-broken (ADR 21). Import the C-extension itself.
python -c "import torch,vllm; import vllm.vllm_flash_attn._vllm_fa2_C as _; \
print('OK torch',torch.__version__,'vllm',vllm.__version__)" 2>&1 | tail -3
echo "   if that fails: pip install --no-deps --force-reinstall \\"
echo "     torch==2.11.0 torchvision==0.26.0 torchaudio==2.11.0"

if [ "${RATE:-0}" = "1" ]; then
  hr "11. THROUGHPUT (60 s)"
  cnt(){ wc -l "$SCRATCH"/harnesslab/mvp_grid/rollouts_*/rollouts.jsonl 2>/dev/null \
         | tail -1 | awk '{print $1}'; }
  a=$(cnt); sleep 60; b=$(cnt)
  printf "  %d -> %d  =  %d rollouts/min  (~%d/h)\n" "$a" "$b" "$((b-a))" "$(((b-a)*60))"
fi
echo
