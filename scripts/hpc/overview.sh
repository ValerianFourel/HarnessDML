#!/bin/bash
# Full-view snapshot of the whole experiment on JUPITER: code version, quotas,
# jobs now, outcomes, per-slice progress against each spec's own target, what
# is still gated-but-unfinished, server health, harvested results, venv.
# Login node.
#
#   bash scripts/hpc/overview.sh          # snapshot (raw line counts)
#   DEEP=1 bash scripts/hpc/overview.sh   # read the stores: in-scope, de-duplicated
#                                         #   progress (minutes on a census)
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
echo "-- uncommitted / untracked on this clone (harvested results live here):"
git status --porcelain | head -10

hr "1. QUOTAS  (a full \$HOME silently kills EVERY job at startup)"
du -sh "$HOME/.cache" 2>/dev/null
[ -n "${SCRATCH:-}" ] && du -sh "$SCRATCH/harnesslab" 2>/dev/null
jutil user projects 2>/dev/null | head -3

hr "2. JOBS RIGHT NOW"
printf "running=%s  pending=%s\n" \
  "$(squeue -u "$USER" -h -t R | wc -l)" "$(squeue -u "$USER" -h -t PD | wc -l)"
squeue -u "$USER" -o "%.11i %.9T %.30j %.9M %.10L %R" | head -60
echo "-- what each RUNNING job is serving / last slice it reported:"
for j in $(squeue -u "$USER" -h -t R -o %i); do
  m=$(grep -m1 '\[serve\]' "slurm-$j.out" 2>/dev/null | awk '{print $2}')
  last=$(grep -h '\[run\]' "slurm-$j.out" 2>/dev/null | tail -1 | cut -c1-90)
  printf "  %-11s %-24s %s\n" "$j" "${m:-?}" "${last:-<first bench still running>}"
done

hr "3. PENDING: why  ((Dependency) = healthy resume chain)"
squeue -u "$USER" -h -t PD -o "%R" | sort | uniq -c | sort -rn
# running=0 with a full queue reads like a disaster and is usually just this
if squeue -u "$USER" -h -t PD -o "%R" | grep -qi "reserv\|maint"; then
  echo
  echo "  >> CLUSTER MAINTENANCE RESERVATION — jobs cannot start until it lifts."
  echo "     Nothing is broken and nothing needs resubmitting; chains resume by"
  echo "     themselves. When does it end:"
  scontrol show reservation 2>/dev/null | grep -E "ReservationName|StartTime|EndTime" \
    | head -6 | sed 's/^/       /'
fi

hr "4. OUTCOMES — last 24 h  (Start included: old incidents look current without it)"
sacct -u "$USER" --starttime now-24hours -X -n -o State%14 2>/dev/null \
  | awk '{print $1}' | sort | uniq -c | sort -rn
echo "-- anything not COMPLETED/RUNNING/PENDING, newest last:"
sacct -u "$USER" --starttime now-24hours -X -n \
  -o JobID%12,Start%20,State%12,Elapsed%10,ExitCode 2>/dev/null \
  | grep -vE "COMPLETED|RUNNING|PENDING" | tail -15
echo "   exit 3 = api-error resume path (rollouts stay pending, harmless)"
echo "   exit 4 = serve never healthy by the 40-min ceiling -> check §9"
echo "   exit 6 = serve-path preflight caught a broken compiled stack (ADR 21)"

hr "5. PROGRESS — roster by model, then every slice against ITS OWN target"
python -m harnesslab.cli progress --roster ${DEEP:+--deep}

hr "6. RUNNING SERVERS: healthy? producing? real errors?"
# grep for the ABI break by its exact message — a transformers deprecation
# warning contains the bare word "torchvision" and would false-positive.
for j in $(squeue -u "$USER" -h -t R -o %i); do
  log="$SCRATCH/harnesslab/serverlogs/${j}_8001.log"
  [ -f "$log" ] || { echo "--- job $j --- (no server log yet)"; continue; }
  echo "--- job $j ---"
  grep -m2 -E "torchvision::nms does not exist|_vllm_fa[23]_C|illegal memory|Disk quota|CUDA error|^ValueError|^RuntimeError" \
    "$log" | sed 's/^/   REAL-ERR> /'
  echo "   last server line: $(tail -1 "$log" | cut -c1-120)"
done

hr "7. HARVESTED RESULTS (results/ — tracked vs not)"
tracked=$(git ls-files results/ | cut -d/ -f2 | sort -u)
ondisk=$(ls -1 results/ 2>/dev/null | sort -u)
echo "  tracked in git: $(printf "%s" "$tracked" | grep -c .)"
untracked=$(comm -13 <(printf "%s\n" "$tracked") <(printf "%s\n" "$ondisk"))
if [ -n "$untracked" ]; then
  echo "  NOT COMMITTED (harvest done, results not pushed — run harvest_all.sh):"
  printf "%s\n" "$untracked" | sed 's/^/    /'
fi
echo "-- recent results commits:"
git log --oneline -5 -- results/ | sed 's/^/  /'

hr "8. PROBE + PILOT VERDICTS — last 24 h"
sacct -u "$USER" --starttime now-24hours -X -n -o JobID%12,JobName%24,State%12 2>/dev/null \
  | grep -Ei "probe|pilot" | while read -r jid jname jstate; do
  m=$(grep -m1 '\[serve\]' "slurm-${jid}.out" 2>/dev/null | awk '{print $2}')
  v=$(grep -hoE "Action: [A-Za-z]+\[|Answer:|FATAL|healthy|ValueError:" "slurm-${jid}.out" 2>/dev/null \
      | sort -u | tr '\n' ' ')
  printf "  %-11s %-22s %-11s %-24s :: %s\n" "$jid" "$jname" "$jstate" "${m:-?}" "${v:-<no verdict>}"
done

hr "9. VENV INTEGRITY (serve path, not just 'import vllm')"
# flash-attn loads lazily at `vllm serve`, so a bare import passes even when
# the compiled stack is ABI-broken (ADR 21). Import the C-extension itself.
python -c "import torch,vllm; import vllm.vllm_flash_attn._vllm_fa2_C as _; \
print('OK torch',torch.__version__,'vllm',vllm.__version__)" 2>&1 | tail -3
echo "   if that fails: pip install --no-deps --force-reinstall \\"
echo "     torch==2.11.0 torchvision==0.26.0 torchaudio==2.11.0"

if [ "${RATE:-0}" = "1" ]; then
  hr "10. THROUGHPUT (60 s)"
  cnt(){ wc -l "$SCRATCH"/harnesslab/mvp_grid/rollouts_*/rollouts.jsonl 2>/dev/null \
         | tail -1 | awk '{print $1}'; }
  a=$(cnt); sleep 60; b=$(cnt)
  printf "  %d -> %d  =  %d rollouts/min  (~%d/h)\n" "$a" "$b" "$((b-a))" "$(((b-a)*60))"
fi
echo
