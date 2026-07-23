# Architecture — how the system works

## Three environments, GitHub is the only bus

```
LOCAL (Mac + Claude Code)          GITHUB (single main)         JUPITER (JSC)
  writes all code/configs/tests ──► code paths ──────────────►  git pull
  reviews results, Phase-5          results/ + lock files ◄──   commits ONLY small
  analysis from results/       ◄──                              aggregated artifacts
```

Path discipline instead of branches: local commits touch code paths, JUPITER
commits `results/`, `configs/tasks/`, `configs/model_revisions.lock.yaml`.
Raw rollout text NEVER enters git: a pre-commit guard
(`scripts/hooks/pre-commit`, installed via `git config core.hooksPath
scripts/hooks`) rejects commits adding >20 MB or any `**/rollouts/*.jsonl`.

## Data flow of one experiment

```
configs/experiments/X.yaml ──► ExperimentSpec (+ --set overrides)
        │
        ▼
runner: triples = configs × tasks × seeds
        │  seeded random interleave (schedule.py) — no config runs contiguously
        │  skip rollout_keys already in the store (resume by construction)
        ▼
agent loop (fixed, identical for every config)
        │  compose() system prompt: base + ON components (ordering, template)
        │                            + universal Answer: instruction
        │  strict grammar: one Action per message, retry-once on parse failure
        │  T on  → ToolBox (QA docstore | math calculator)   T off → no tools
        │  confidence elicitation turn after Answer
        ▼
grader (deterministic): qa_f1 | numeric | sympy (fallback logged per row)
        ▼
RolloutStore  $SCRATCH/.../rollouts.jsonl   ← 47-column schema-exact rows
        │     api_error rollouts → failures.jsonl (NOT done; retried on resume)
        ▼
aggregate → results/<exp_id>/panel.parquet + cell_metrics.parquet
            + manifest_index.json + REPORT.md      (committed from login node)
```

Every job writes a manifest (git SHA, config hash, model hf_id + pinned
revision, sampling params, component-template hashes, node, timestamps); a
panel row that cannot resolve to its manifest is a bug by definition.

## Module map (`harnesslab/`)

- **`protocol.py`** — the ONE textual grammar: `Action: Verb[arg]` (line-
  anchored, case-sensitive), `Answer:` extraction (last line wins),
  confidence parsing. Shared by composer, loop, and graders.
- **`components/`** — one file per component with 3 frozen paraphrase
  variants; `compose()` assembles base header + ON blocks (3 orderings) +
  submission line; supports the bridge arm (CCI-style submission coupled
  into T) and length-matched padding pseudo-components. Every rendered block
  is content-hashed into manifests; 576 golden prompt hashes pin the freeze.
- **`agent/loop.py`** — the fixed ReAct-style loop. finish_reason semantics:
  `answered | parse_loop (malformed action ×2) | no_answer (prose ×2) |
  step_cap | timeout | api_error`. Answer beats Action if both appear.
- **`tools/`** — hermetic: DocStore with ReAct Search/Lookup semantics over
  the task's shipped paragraphs; asteval calculator whose sandbox rejects
  imports, names, attribute access, dunders. Nothing touches the network on
  compute nodes.
- **`graders/`** — SQuAD-normalized token-F1/EM with alias max (QA); Decimal
  numeric equality vs `#### n` golds (GSM8K); sympy canonicalization +
  symbolic/numeric equivalence with a logged string fallback (MATH).
- **`metrics/`** — pure, fixture-tested: C_out, pairwise JSD / normalized
  Levenshtein trajectory consistency, C_res = exp(−mean CV), pass@k/pass∧k,
  ECE (10 bins), tie-aware AUROC, Brier.
- **`store/`** — append-only JSONL keyed by `hash(cell, task, seed)`;
  idempotent appends; tolerates a corrupt trailing line (killed job) and
  never glues onto it; `failures.jsonl` for api_errors (kept pending).
- **`schedule.py`** — seeded shuffle of the rollout queue + run-length
  diagnostic (tested interleaving property).
- **`client/`** — `OpenAICompatClient` (httpx, retries/backoff, per-request
  seed), `MultiEndpointClient` (round-robin over the 4 per-node servers),
  `MockClient` (the only backend tests use). The served model name is always
  resolved to the registry `hf_id` — never the registry key.
- **`panel.py`** — `load_panel(covariates=...)` hard-errors unless every
  covariate has role treatment/context/pre_treatment in
  `schema/column_roles.yaml`. Mediators (turns, tokens, tool calls,
  trajectory features) are never controls.
- **`experiment.py`** — spec loading with `--set` overrides; model registry +
  revisions lock merge; `served_model_name()`.
- **`fits.py`** — params × dtype (bf16/fp8) × 1.35 overhead vs GH200 memory
  → serving mode; `fits-check` CLI validates every registry entry.
- **`cli.py`** — `run | aggregate | status | budget | verify | fits-check`.
  `budget` refuses any experiment without a measured pilot-throughput
  constant; `run` exits 3 if any rollout hit a terminal API error.

## Serving on JUPITER (every job = one full 4×GH200 node)

- `one_gpu` models (fit a single 96 GB GPU): **4 independent vLLM replicas**,
  one pinned per GPU, ports 8001–8004, client round-robins.
- `one_node_tp4` models: one server, `--tensor-parallel-size 4`.
- `scripts/hpc/env.sh` is sourced by every shell AND every sbatch script:
  module load (venv python links against the module's libpython), venv
  activation, `$SCRATCH` resolution from `$SCRATCH_<project>`.
- `slurm/run_experiment.sbatch`: serve → health-check loop → run one or
  several benchmarks **sequentially against the same warm servers**
  (`BENCH=a,b,c`), servers killed on exit. One model per node; different
  models = different concurrent jobs.

## Schemas

`schema/panel_schema.yaml` defines the 47-column rollout row (identity/
provenance, treatments, context, pre-treatment, outcomes, post-treatment)
and the cell-metrics table; `schema/column_roles.yaml` assigns every column
exactly one causal role; tests enforce 1:1 coverage between the two files.

## Testing philosophy

All 114 tests run locally in seconds against the mock backend only: golden
prompts (hash-frozen), grammar/loop branches, tool determinism and sandbox
escapes, grader parity fixtures, hand-computed metric values, store
corruption/resume, interleaving property, role-guard hard errors, a real
`git commit` rejected by the size guard, and an end-to-end mock experiment
(run → resume no-op → aggregate → schema-exact panel). pytest green is a
precondition for emitting any sbatch as "ready".
