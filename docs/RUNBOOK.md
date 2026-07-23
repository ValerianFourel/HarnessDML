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

## Monitoring

```sh
squeue -u $USER
sacct -j <jobid> -X --format=JobID,State,Elapsed
tail -f slurm-<jobid>.out
tail -f $SCRATCH/harnesslab/serverlogs/<jobid>_8001.log
python -m harnesslab.cli status --rollouts $SCRATCH/harnesslab/<exp>/rollouts_<model>_<bench>
```

## Shipping results (login node)

```sh
python -m harnesslab.cli aggregate --rollouts $SCRATCH/harnesslab/<exp>/rollouts_<m>_<b> \
  --out results/<exp>_<m>_<b>
python -m harnesslab.cli verify --panel results/<exp>_<m>_<b>/panel.parquet
git add results/ && git commit -m "results: ..." && git push
```

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
