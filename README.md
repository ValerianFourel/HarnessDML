# HarnessDML

Causal re-analysis of the Holistic Agent Leaderboard (HAL) rollouts
([arXiv:2510.11977](https://arxiv.org/abs/2510.11977)) using Double Machine
Learning. Mission and phase plan: see [CLAUDE.md](CLAUDE.md).

## Status

- [ ] Phase 0 — environment, acquisition, empirical schema report (in progress)
- [ ] Phase 1 — ETL to analysis panel
- [ ] Phase 2 — design diagnostics
- [ ] Phase 3 — DML estimation
- [ ] Phase 4 — report & figures

## Setup

```sh
uv sync                                  # create .venv with pinned deps
git clone --depth 1 https://github.com/princeton-pli/hal-harness vendor/hal-harness
# hal-harness gets its own venv (see below) so its deps never touch ours
```

## Data

Traces live in the public HF dataset `agent-evals/hal_traces` (~113 GB, one
encrypted zip per run, flat layout). Never commit anything under `data/`.

```sh
uv run python scripts/hf_inventory.py    # per-benchmark size/count table -> reports/hf_inventory.md
```
