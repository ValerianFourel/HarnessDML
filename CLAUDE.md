# HarnessDML — Causal Re-Analysis of HAL Agent Rollouts via Double Machine Learning

## Mission

Build a reproducible pipeline that re-analyzes the Holistic Agent Leaderboard (HAL) dataset — 21,730 agent rollouts across 9 models, 9 benchmarks, and multiple scaffolds (arXiv:2510.11977) — from a **causal inference** perspective using **Double Machine Learning**. The published analysis is descriptive (raw Pass@1 spreads, Pareto plots, single runs, no adjustment, no uncertainty). Our contribution: orthogonalized, cross-fitted treatment-effect estimates of harness/config choices with valid clustered inference, effect heterogeneity (GATEs), and sensitivity analysis for unmeasured confounding.

The user is an experienced DoubleML user — do not simplify the econometrics. When in doubt, follow Chernozhukov et al. (2018) conventions.

## Data source

- Traces: Hugging Face dataset `agent-evals/hal_traces` (~113 GB total, files are **encrypted** — this is why naive loading fails with JSON parse errors).
- Decryption: `hal-decrypt` CLI from `https://github.com/princeton-pli/hal-harness` (repo is archived but installable; `pip install -e .` after cloning, plus `cryptography`).
- Traces were logged via Weave: each rollout contains the full LLM call tree, token counts, and dollar costs.
- Benchmarks span coding (SWE-bench Verified Mini, USACO), web (Online Mind2Web, AssistantBench, GAIA), science (CORE-Bench Hard, ScienceAgentBench, SciCode), customer service (TAU-bench Airline).

**Do NOT download all 113 GB.** Use `huggingface_hub.snapshot_download` with `allow_patterns` to pull ONE benchmark slice first (prefer `taubench` or `swebench_verified_mini` — smallest useful slices). Scale out only after the pipeline works end-to-end.

## Causal framing (read carefully — this governs all code)

- **Unit of observation:** one rollout = (task, model, scaffold, config, run).
- **Outcomes Y:** primary = binary success; secondary = log(total_cost_usd + ε), completion tokens, wall-clock.
- **Candidate treatments D (estimate separately, one estimand at a time):**
  1. `reasoning_effort` — the cleanest treatment in HAL. The paper claims higher reasoning effort *reduced* accuracy in 21 of 36 settings, from single runs with no adjustment. Estimand #1: does this survive orthogonalization and clustered inference?
  2. `scaffold` identity (multi-valued) — pairwise contrasts vs. a reference scaffold, within model.
  3. `model` identity — only as a benchmark of the method (sanity check: adjusted model effects should be large and stable).
- **Pre-treatment covariates X:** benchmark, task identity/difficulty, model identity (when model is not the treatment), prompt/task length, benchmark-domain dummies.
- **STRICT post-treatment rule:** number of steps, tool calls, tokens consumed, retries, termination reason are **mediators/outcomes, never controls**. Maintain a column registry (`schema/column_roles.yaml`) tagging every variable as `treatment | outcome | pre_treatment | post_treatment`. Any estimation function must refuse to accept a `post_treatment` column in X. Write a unit test for this guard.
- **Assignment mechanism is observational:** HAL chose configurations "prioritizing configurations that reveal meaningful comparisons" — assignment correlates with model and benchmark. Treat this as observational data with known-partial support, not a factorial experiment.

## Phase 0 — Environment & acquisition

1. Python 3.11+, `uv` for env. Deps: `huggingface_hub`, `cryptography`, `polars` (or pandas), `pyarrow`, `doubleml>=0.9`, `lightgbm`, `scikit-learn`, `statsmodels`, `matplotlib`, `pytest`, `pyyaml`.
2. Clone and install `hal-harness`; verify `hal-decrypt` runs on one file.
3. Download ONE benchmark slice; decrypt into `data/raw/<benchmark>/`.
4. Write `scripts/discover_schema.py`: walk N decrypted traces, emit an empirical schema report (`schema/SCHEMA.md`) — key paths, types, presence rates. **Do not hardcode assumed field names anywhere else; everything downstream reads from a mapping config derived from this report.** If the real schema contradicts anything in this prompt, stop, update `SCHEMA.md`, and ask the user before proceeding.

## Phase 1 — ETL to analysis panel

Build `scripts/build_panel.py` → `data/panel/<benchmark>.parquet`, one row per rollout:

`rollout_id, benchmark, domain, task_id, model, model_family, reasoning_effort, scaffold, temperature?, success, total_cost_usd, prompt_tokens, completion_tokens, reasoning_tokens?, n_llm_calls, n_tool_calls, wall_clock_s, termination_reason`

- Parse costs/tokens from the Weave call tree; success from the benchmark's scored result field.
- Validation tests: total rollouts across all slices should reconcile toward ≈21,730; report per-slice counts vs. the paper; missingness table; duplicate rollout detection.
- Keep raw-trace parsing isolated in one module so a Spark port is trivial later (the ETL may be lifted into doubleml-pyspark for the full 113 GB — design for that, don't implement it yet).

## Phase 2 — Design diagnostics BEFORE any estimation

`scripts/diagnostics.py` must produce, per treatment:

1. Support cross-tabs: model × scaffold × benchmark × reasoning cells with counts; an overlap heatmap; a machine-readable list of estimable contrasts (cells with n ≥ threshold on both arms).
2. Propensity diagnostics: fit e(X) per binary contrast, plot distributions, report overlap after trimming at [0.02, 0.98]; log trimmed share.
3. Task-difficulty construction: leave-one-config-out mean success per task, computed **inside cross-fitting folds only** (never on the estimation fold — leakage guard + test). Where a task appears under enough configs, prefer task fixed effects via within-task contrasts.
4. A written `reports/design_notes.md` describing the assignment mechanism and which estimands are identified on which strata. **No estimation runs until this exists.**

## Phase 3 — Estimation

`scripts/estimate.py`, config-driven (`configs/*.yaml`), each run = one estimand:

- **Primary estimator:** `DoubleMLIRM` for binary contrasts (e.g., reasoning high vs. none within model×benchmark strata); `DoubleMLPLR` for continuous/ordinal dose (reasoning token budget if recoverable). LightGBM nuisances, 5-fold cross-fitting, 3 repetitions (`n_rep=3`).
- **Clustering:** cluster at `task_id` (DoubleML cluster-robust inference). Rollouts sharing a task are not independent — never report unclustered SEs.
- **Nuisance tuning:** tune LightGBM via the DoubleML tuning interface on a held-out scheme; log chosen params.
- **Multi-valued scaffold:** loop pairwise IRM contrasts vs. reference; collect into one results frame.
- **GATEs:** by domain (coding/web/science/customer service), by model, by task-difficulty tercile. Use DoubleML GATE machinery, not post-hoc subgroup refits.
- **Comparison ladder (headline deliverable):** for each estimand report side-by-side (a) naive difference in means, (b) task-clustered OLS with additive controls (the "Adding Error Bars to Evals" baseline), (c) DML. One table + one forest plot. The story is what adjustment and orthogonalization change.
- **Multiplicity:** multiplier bootstrap for simultaneous CIs across contrasts; Romano–Wolf or Holm-adjusted p-values in all summary tables.
- **Sensitivity:** DoubleML `sensitivity_analysis` (omitted-variable-bias bounds, Chernozhukov et al. 2022). Benchmark the confounding strength against the strongest measured covariate (model identity or benchmark). Report robustness values; contour plot per primary estimand.

## Phase 4 — Outputs

- `reports/ANALYSIS.md`: estimand definitions, identification assumptions stated honestly (unconfoundedness given X on overlapping strata; no interference across rollouts — flag shared-infra caveats), results tables, limitations.
- Figures: naive-vs-adjusted forest plot, GATE plots with simultaneous bands, overlap heatmap, sensitivity contours. Matplotlib, no seaborn, colorblind-safe.
- Full reproducibility: `run.sh` (or make targets) executing Phases 0→4 for one benchmark slice end-to-end; fixed seeds; environment lockfile.

## Guardrails (enforce in code + tests)

1. No post-treatment covariates in X — hard error, tested.
2. No pooling across non-overlapping strata — estimable-contrast list is the single source of truth.
3. Every reported estimate carries: n per arm, n clusters, trimming share, cluster-robust CI.
4. Difficulty covariates computed only via leakage-safe cross-fitting.
5. If any HAL number can't be reconciled (rollout counts, the 21/36 reasoning claim), document the discrepancy in `reports/discrepancies.md` — do not silently adjust.

## Working style

Start with Phase 0 only. Show the schema report before writing the ETL. Small commits, one phase per PR-sized chunk, pytest green before moving on. Ask before any download > 5 GB.
