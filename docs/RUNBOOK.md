# Runbook — operating HarnessLab

## Local development loop

```sh
uv sync && uv run pytest             # 114 tests, mock backend, ~8 s
uv run ruff check harnesslab/ tests/
uv run python -m harnesslab.cli fits-check
git config core.hooksPath scripts/hooks    # size guard (once per clone)
```

Golden prompts are frozen: `uv run python scripts/regen_goldens.py` ONLY on a
deliberate, reviewed template change (drift otherwise fails tests).

## JUPITER: one-time setup (login node)

```sh
cd /e/project1/scifi/fourel1/HarnessDML/HarnessDML
git config core.hooksPath scripts/hooks
bash scripts/hpc/setup_env.sh        # modules + venv + harnesslab[data] + vLLM
export HF_TOKEN=...                  # keep it in .env, not shell history
```

## After ANY change to the venv (login node)

```sh
bash scripts/hpc/check_env.sh     # walks the real `vllm serve` import chain
```

`import vllm` is not a check: flash-attn loads lazily at serve time (ADR 21)
and the transformers/huggingface_hub layer is never touched at all (ADR 24).
Never `pip install` while jobs are starting — pip unlinks before it relinks,
and a job importing during that window dies on a half-written package while
the same import succeeds a second later on the login node.

## JUPITER: every new shell

```sh
cd /e/project1/scifi/fourel1/HarnessDML/HarnessDML
source scripts/hpc/env.sh
```

This is mandatory, not cosmetic: it loads the modules the venv's python is
linked against, activates the venv, and resolves `$SCRATCH` from
`$SCRATCH_<project>`. Batch scripts source it themselves.

## Data & weights (login node, network)

```sh
python scripts/build_tasks.py --all              # seeded N=100 task lists → commit
bash scripts/hpc/prefetch_models.sh --model-id gpt_oss_20b gpt_oss_120b ...
git add configs/tasks configs/model_revisions.lock.yaml && git commit && git push
```

Prefetch pins revision SHAs to `configs/model_revisions.lock.yaml` (commit
it); compute jobs run `HF_HUB_OFFLINE=1` against `$SCRATCH/hf`.
`$SCRATCH` purge: 90 days (auto-cleanup active from 2026-08-01) — everything
there (weights cache, rollouts) is regenerable by design.

## Submitting work

```sh
# one model, one benchmark:
sbatch --export=ALL,EXP=configs/experiments/smoke_live.yaml,MODEL_ID=gpt_oss_20b,BENCH=gsm8k \
  slurm/run_experiment.sbatch
# one model, several benchmarks sequentially on the same warm servers:
sbatch --export=ALL,EXP=configs/experiments/pilot.yaml,MODEL_ID=gpt_oss_20b,BENCH=hotpotqa,musique,gsm8k,math \
  slurm/run_experiment.sbatch
# the whole pilot (both gpt-oss models in parallel, 2 nodes):
bash scripts/hpc/submit_pilot.sh
```

Concurrency rules: any number of jobs across different (model, benchmark)
slices in parallel; exactly one model per node; never run the *same*
(exp, model, benchmark) slice in two simultaneous jobs (shared store file).
Re-submitting a finished or crashed slice is always safe — the store resumes
and completed rollouts are skipped.

Onboarding a model (§6, ADR 16): probe → pilot → gate → census.

```sh
EXP=configs/experiments/pilot.yaml MODEL_ID=<model> BENCH=hotpotqa,musique,gsm8k,math \
  sbatch slurm/run_experiment.sbatch
bash scripts/hpc/gate_report.sh <model>     # BARE/T per band + IN/OUT verdict
# record the ruling in configs/gates.yaml, then chain the bands that came back IN
```

## Monitoring

Two one-shot reports, both read-only and safe mid-census:

```sh
bash scripts/hpc/status.sh              # fast pulse: jobs, stores, census total
bash scripts/hpc/overview.sh            # full view: + code version, quotas, 24h
                                        #   outcomes, per-slice progress, gaps,
                                        #   server health, results, venv check
DEEP=1 bash scripts/hpc/overview.sh     # ... reading the stores (minutes)
RATE=1 bash scripts/hpc/overview.sh     # ... and 60 s of measured throughput
```

Progress alone, with each slice scored against its own spec's target
(configs x in-scope tasks x seeds) and the gate matrix in `configs/gates.yaml`
telling you what is still missing:

```sh
python -m harnesslab.cli progress                 # raw line counts, seconds
python -m harnesslab.cli progress --deep          # in-scope, de-duplicated
python -m harnesslab.cli progress --deep --only qwen_3_5_9b_hotpotqa
```

`--deep` is the one that tells the truth: raw lines include out-of-scope tasks
from before a cap (HotpotQA 7405 -> 3000) and duplicate `(cell, task, seed)`
rows from the ADR 22 re-key, so a store can read past 100% with work pending.

Drilling in:

```sh
squeue -u $USER
sacct -j <jobid> -X --format=JobID,State,Elapsed
tail -f slurm-<jobid>.out
tail -f $SCRATCH/harnesslab/serverlogs/<jobid>_8001.log
python -m harnesslab.cli status --rollouts $SCRATCH/harnesslab/<exp>/rollouts_<model>_<bench>
```

## Shipping results (login node)

Everything at once — aggregate every store, verify each panel, commit, push.
Idempotent, so it is the safe "make git match the cluster" button:

```sh
bash scripts/hpc/harvest_all.sh                 # all of it
ONLY=padding bash scripts/hpc/harvest_all.sh    # one arm
NO_COMMIT=1 bash scripts/hpc/harvest_all.sh     # aggregate + verify only
```

It passes `--task-scope auto`, which derives the task list and cap from each
store's own spec — harvesting a capped slice by hand without `--tasks` ships
its out-of-scope orphans into the panel. One slice at a time:

```sh
python -m harnesslab.cli aggregate --rollouts $SCRATCH/harnesslab/<exp>/rollouts_<m>_<b> \
  --out results/<exp>_<m>_<b> --task-scope auto
python -m harnesslab.cli verify --panel results/<exp>_<m>_<b>/panel.parquet
git add results/ && git commit -m "results: ..." && git push
```

Publishing the panels (login node — compute nodes have no internet):

```sh
export HF_TOKEN=hf_...
python scripts/publish_hf_dataset.py --repo <user>/harnesslab-panels --dry-run
python scripts/publish_hf_dataset.py --repo <user>/harnesslab-panels
```

Uploads `results/` + `schema/` only, so raw text cannot leak; private unless
`--public`. What the dataset contains, slice by slice, with the artifacts a
reuser must know about: **docs/DATA_INVENTORY.md**.

Then hand off for local review ("pull and review/analyze ..."). Aggregation
is light — a login node is fine; `slurm/aggregate.sbatch` exists for
`--dependency=afterok` chains if wanted.

## Troubleshooting (all four have happened)

| symptom | cause | fix |
|---|---|---|
| `error while loading shared libraries: libpython3.12.so.1.0` | venv python links against the Python *module*; shell/job has no modules loaded | `source scripts/hpc/env.sh` in every shell; sbatch templates already do |
| `[prefetch] set HF_HOME or SCRATCH first` / `SCRATCH: unbound variable` | JUPITER defines only `$SCRATCH_<project>` until `jutil env activate` | `env.sh` auto-resolves; or `jutil env activate -p <project>` |
| server log: `404 The model '<key>' does not exist` | vLLM serves the **hf_id**, request used the registry key | fixed — client resolves `hf_id` via `served_model_name()`; `--model` overrides for non-vLLM endpoints |
| `run` exits 3, `api_errors=N` warning | endpoint failures; those rollouts were logged to `failures.jsonl`, NOT persisted | fix the endpoint, resubmit — resume retries exactly those |
| health-check dots forever | model still loading/compiling (first start ≈ 15–20 min) OR the `vllm serve` child died instantly | `tail $SCRATCH/harnesslab/serverlogs/<jobid>_8001.log` and read which |
| `git push` rejected (non-fast-forward) | the other side pushed first (expected; both sides commit) | `git pull --rebase && git push` — path discipline makes conflicts impossible |
| commit rejected: `SIZE GUARD` | staged >20 MB or a `rollouts/*.jsonl` | aggregates only; raw stays on `$SCRATCH` |
