# HAL Causal Re-Analysis (DML) — Split Local/HPC Workflow

## Mission

Re-analyze the Holistic Agent Leaderboard (HAL) dataset — 21,730 agent rollouts across 9 models, 9 benchmarks, multiple scaffolds (arXiv:2510.11977) — from a **causal inference** perspective using **Double Machine Learning**. The published analysis is descriptive (raw Pass@1 spreads, single runs, no adjustment, no uncertainty). Our contribution: orthogonalized, cross-fitted treatment-effect estimates of harness/config choices with cluster-robust inference, GATEs, and sensitivity analysis.

I am an experienced DoubleML user — do not simplify the econometrics. Follow Chernozhukov et al. (2018) conventions.

## Architecture — three environments, GitHub is the bus

1. **LOCAL (this machine, Claude Code):** writes all code, reviews results, writes analysis. Never downloads traces, never runs estimation. Commits only code (`src/`, `notebooks/`, `configs/`, `scripts/`).
2. **HPC (JupyterHub on the cluster):** clones the repo, downloads and decrypts data to scratch, runs ETL + estimation inside Jupyter notebooks, commits **only small computed artifacts** under `results/`, pushes.
3. **GITHUB:** single repo, single `main` branch. Path discipline instead of branches: local commits touch code paths, HPC commits touch `results/` only. Both sides `git pull --rebase` before pushing. Raw data never enters git.

Everything the HPC runs must be executable as: `git pull` → open notebook → Run All. Everything analyzed locally must be reproducible from `results/` alone, without cluster access.

## Data source (HPC-side only)

- Hugging Face dataset `agent-evals/hal_traces` (~113 GB, files **encrypted** — naive loading fails with JSON parse errors by design).
- Decrypt with `hal-decrypt` from `https://github.com/princeton-pli/hal-harness` (archived but installable: clone + `pip install -e .` + `cryptography`).
- Traces are Weave call trees: full LLM call hierarchy, tokens, dollar costs per rollout.
- Benchmarks: coding (SWE-bench Verified Mini, USACO), web (Online Mind2Web, AssistantBench, GAIA), science (CORE-Bench Hard, ScienceAgentBench, SciCode), customer service (TAU-bench Airline).
- **Never download all 113 GB blindly.** `huggingface_hub.snapshot_download` with `allow_patterns`, one benchmark slice first (`taubench` or `swebench_verified_mini`), resumable, to `$HAL_DATA_DIR` on scratch.
- HPC caveat: assume **compute nodes have no internet**. All network steps (HF download, git push/pull, pip installs) live in clearly marked "login/JupyterHub node" cells or a separate `01_download` notebook. Pure-compute notebooks must run offline.

## Causal framing (governs all code)

- **Unit:** one rollout = (task, model, scaffold, config, run).
- **Outcomes Y:** primary binary success; secondary log(total_cost_usd + eps), completion tokens, wall-clock.
- **Treatments D (one estimand per run config):**
  1. `reasoning_effort` — cleanest. HAL claims higher effort *reduced* accuracy in 21/36 settings from single unadjusted runs. Estimand #1: does that survive DML + clustering?
  2. `scaffold` (multi-valued) — pairwise contrasts vs. reference scaffold, within model.
  3. `model` — method sanity check only (adjusted effects should be large, stable).
- **Pre-treatment X:** benchmark, domain, task identity/difficulty, model (when not treatment), task-prompt length.
- **STRICT post-treatment rule:** steps, tool calls, tokens consumed, retries, termination reason are mediators/outcomes — **never controls**. Column registry `schema/column_roles.yaml` tags every column `treatment | outcome | pre_treatment | post_treatment`; estimation functions hard-error on `post_treatment` in X; pytest covers the guard.
- **Observational assignment:** HAL curated configs ("prioritizing configurations that reveal meaningful comparisons") — assignment correlates with model and benchmark. Partial support is expected; estimands are defined only on overlapping strata.

## Repo layout

```
halcausal/
  src/halcausal/        # ALL logic lives here (etl, diagnostics, estimation, io, guards)
  notebooks/            # THIN orchestration only: import package, call functions, display
    00_hpc_setup.ipynb        # env bootstrap, auth checks, scratch paths
    01_download_decrypt.ipynb # network-required, login node
    02_build_panel.ipynb
    03_diagnostics.ipynb
    04_estimate.ipynb
    05_export_results.ipynb   # manifest + git add results/ + push
  configs/              # yaml per estimand; env.yaml reads $HAL_DATA_DIR
  scripts/              # slurm templates (optional escape hatch), size-guard hook
  schema/               # SCHEMA.md (empirical), column_roles.yaml
  results/              # ONLY committed artifacts (see contract)
  data/ -> $HAL_DATA_DIR   # .gitignored symlink; raw + decrypted + parquet cache
```

Notebooks contain zero business logic — every line of substance must be reviewable locally in `src/` without running anything. Rationale: Claude Code reviews diffs, not notebook outputs.

## Results contract (what HPC is allowed to commit)

Everything in `results/` must be small, final, and self-describing:

- `results/panel/<benchmark>.parquet` — the flat analysis panel (21k rows total is trivially small; commit it so local analysis never needs the cluster).
- `results/diagnostics/` — overlap heatmap data (csv), propensity summaries, estimable-contrast list (json), cell-count tables.
- `results/estimates/<estimand_id>/` — point estimates + cluster-robust CIs (csv), full comparison ladder (naive / clustered-OLS / DML), GATE tables, bootstrap draws (npz/csv) for local re-plotting, sensitivity-analysis output (robustness values, contour grid csv).
- `results/figures/` — png, colorblind-safe, matplotlib.
- `results/manifests/<run_id>.json` — **mandatory per run**: code git SHA, config hash, seeds, package versions (`pip freeze` digest), hostname, timestamps, input slice checksums, rollout counts. Every artifact filename embeds `<run_id>`.
- Size guard: `scripts/check_results_size.py` run by `05_export_results` — hard-fail on any file > 25 MB or any path outside `results/`. Raw/decrypted traces and anything under `data/` are unpushable by construction (.gitignore + guard).

## Auth (document in README, never commit secrets)

- HPC: `HF_TOKEN` env var for the dataset; GitHub fine-grained PAT or deploy key **with write access limited to this repo**, stored in `~/.git-credentials` or ssh key on the cluster, referenced never in code.
- Local: normal GitHub auth. `.env.template` lists required vars; `.env` gitignored.

## Phases

**Phase 0 — skeleton (LOCAL, now).** Scaffold the repo, package, configs, guards, size-check, .gitignore, README with the exact HPC bootstrap sequence (module load / micromamba fallback, `uv` or venv, `pip install -e .`, hal-harness install), and the six thin notebooks as stubs. Deps: `huggingface_hub, cryptography, polars, pyarrow, doubleml>=0.9, lightgbm, scikit-learn, statsmodels, matplotlib, pytest, pyyaml, papermill(optional)`. Push. Stop and show the tree before writing any ETL.

**Phase 1 — schema discovery (HPC runs, LOCAL writes).** `01_download_decrypt` pulls ONE slice, decrypts to scratch. `discover_schema()` walks N traces, emits `schema/SCHEMA.md` (key paths, types, presence rates) → HPC commits it under results-contract exception (schema/ is HPC-writable too). Schema is reviewed locally before ETL. **No field names hardcoded anywhere until SCHEMA.md exists; if reality contradicts this prompt, we update the prompt, not silently the code.**

**Phase 2 — ETL (HPC).** `build_panel()` → one row per rollout: `rollout_id, benchmark, domain, task_id, model, model_family, reasoning_effort, scaffold, temperature?, success, total_cost_usd, prompt_tokens, completion_tokens, reasoning_tokens?, n_llm_calls, n_tool_calls, wall_clock_s, termination_reason`. Reconciliation tests vs. paper counts (→ ~21,730 across slices); missingness + duplicate reports into `results/diagnostics/`. Keep trace-parsing in one module — it may be ported to doubleml-pyspark for the full corpus later; design for that, don't build it.

**Phase 3 — design diagnostics before estimation (HPC).** Support cross-tabs (model × scaffold × benchmark × reasoning), overlap heatmap, machine-readable estimable-contrast list (n ≥ threshold both arms), propensity distributions with [0.02, 0.98] trimming and trimmed-share logging, leakage-safe task-difficulty covariate (leave-one-config-out mean success computed inside folds only — tested). `results/diagnostics/design_notes.md` states the assignment mechanism and which estimands are identified where. **Estimation notebooks refuse to run if this file is absent.**

**Phase 4 — estimation (HPC).** Config-driven, one estimand per config: `DoubleMLIRM` for binary contrasts (LightGBM nuisances, 5-fold cross-fitting, `n_rep=3`), `DoubleMLPLR` for ordinal/continuous dose; **cluster-robust at `task_id` always**; nuisance tuning via DoubleML interface, params logged; pairwise scaffold contrasts vs. reference; GATEs by domain, model, difficulty tercile via DoubleML GATE machinery (no post-hoc subgroup refits); multiplier bootstrap simultaneous CIs + Romano–Wolf/Holm across contrasts; DoubleML `sensitivity_analysis` benchmarked at the strongest measured covariate. **Comparison ladder is a headline deliverable:** naive diff-in-means vs. task-clustered OLS (Miller-style baseline) vs. DML, one table + forest plot per estimand. Export everything per the results contract, manifest included, push.

**Phase 5 — analysis (LOCAL, Claude + user).** `git pull`, then working only from `results/`: interpret the ladder (what did adjustment change and why), GATE narratives, sensitivity verdicts, reconciliation with HAL's 21/36 claim, limitations. Deliverable `reports/ANALYSIS.md` (local-committed): estimands, identification assumptions stated honestly (unconfoundedness given X on overlapping strata; no interference — flag shared-infrastructure caveats), results, what a designed factorial in Inspect should target next. Any discrepancy with published HAL numbers goes to `reports/discrepancies.md` — never silently adjusted.

## Guardrails (enforced in code + tests)

1. No post-treatment covariates in X — hard error, tested.
2. No pooling across non-overlapping strata — the estimable-contrast list is the single source of truth.
3. Every estimate ships with n per arm, n clusters, trimming share, cluster-robust CI, run_id.
4. HPC pushes only `results/` + `schema/`; local pushes only code paths; both rebase-pull before push; size guard blocks everything else.
5. Notebooks thin, package fat; pytest green locally before any push that HPC will consume.
6. Ask before any download > 5 GB or any full-corpus run.

## Working style

Start with Phase 0 only. Show the repo tree and the README's HPC bootstrap section before anything else. Small commits, one phase per chunk. When HPC results land, the user says "pull and analyze <run_id>" — then work strictly from `results/` and the manifest.
