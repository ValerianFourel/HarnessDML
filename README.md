# HarnessLab

A factorial experiment platform that treats **agent-harness components as
randomized treatments** and estimates their causal effects on a vector of
outcomes — accuracy, cost, run-to-run consistency, calibration — across
open-weight model families, self-hosted with vLLM on the JUPITER
supercomputer (JSC).

The one-sentence goal: leaderboards compare *bundled* harnesses; we make the
individual components (Planning, Tool Use, Memory, Structured Reasoning,
Reflection) **identifiable causes**, with real inference — interactions,
sign-flips across models, simultaneous confidence bands — instead of
single-run deltas.

## Documents

| file | what it is |
|---|---|
| [CLAUDE.md](CLAUDE.md) | the governing specification (phases, design, non-negotiables) |
| [ESTIMANDS.md](ESTIMANDS.md) | what we estimate and what we refuse to claim |
| [docs/OVERVIEW.md](docs/OVERVIEW.md) | the scientific story: why, prior art, design |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | how the system works, module by module |
| [docs/RUNBOOK.md](docs/RUNBOOK.md) | operations: local dev, JUPITER, troubleshooting |
| [docs/PROGRESS.md](docs/PROGRESS.md) | journal: everything done so far, incidents included |
| [docs/DECISIONS.md](docs/DECISIONS.md) | decision log (ADR-lite) |

## Status

- [x] Phase M — migration (HAL observational arm preserved in `legacy/hal-reanalysis/`)
- [x] Phase 0 — schemas, size guard, ESTIMANDS.md
- [x] Phase 1 — components, loop, tools, graders, metrics, store, mock client — 114 tests
- [x] Phase 3 — JUPITER provisioning (env, prefetch, serving, sbatch, task lists, registry)
- [ ] Phase 2 — live smoke on JUPITER (in progress: rerun after served-name fix)
- [ ] Phase 4 — pilot (difficulty gate + throughput constants)
- [ ] Phase 5 — MVP grid (Tier F+G × gated bands, 2⁵ factorial, K=5 seeds)
- [ ] Phase 6 — panel v1.0 freeze + DATASHEET

## Quickstart (local)

```sh
uv sync                      # Python 3.12 venv + all deps
uv run pytest                # full suite, mock backend only, ~8 s
uv run python -m harnesslab.cli fits-check
```

GPU execution never happens locally — see [docs/RUNBOOK.md](docs/RUNBOOK.md)
for the JUPITER side.

## Repo map

```
harnesslab/            the library (components, agent loop, tools, graders,
                       metrics, store, schedule, clients, panel guard, CLI)
configs/models.yaml    tiered model registry (hub-resolved params, serving modes)
configs/tasks/         committed seeded task lists (N=100 per benchmark-band)
configs/experiments/   experiment specs (smoke_live, pilot, ...)
schema/                panel schema (47 columns) + causal-role registry
scripts/hpc/           JUPITER: env.sh, setup, prefetch, serving, submit helpers
slurm/                 sbatch templates (one model per node, benches sequential)
tests/                 114 tests incl. 576 golden prompts + grader parity fixtures
results/               ONLY contract-compliant artifacts (panels, metrics, reports)
legacy/hal-reanalysis/ preserved observational arm (paused, do not delete)
```

Everything raw (rollout JSONL with prompts/completions) lives on `$SCRATCH`
and never enters git — a pre-commit guard (`git config core.hooksPath
scripts/hooks`) rejects >20 MB commits and any `rollouts/*.jsonl`.
