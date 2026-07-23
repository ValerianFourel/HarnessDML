# CLAUDE.md — HarnessDML → HarnessLab MVP (full repo transformation)

You are Claude Code working in `/Users/valerianfourel/Hamburg/HarnessDML`. This document is the complete, self-contained specification. Read it fully, then execute **one phase per session-chunk**, stopping at every STOP for my review. Do not skip phases, do not merge phases, do not start coding before Phase M is approved.

---

## 0. Mission

Transform this repository into **HarnessLab**: a factorial experiment platform that treats agent-harness *components* as randomized treatments and estimates their causal effects on a vector of outcomes (accuracy, cost, run-to-run consistency, calibration) across multiple open-weight model families served with vLLM on the JUPITER supercomputer.

Scientific synthesis (three legs, none sufficient alone):
- **CCI** (arXiv:2605.05716): 5 binary scaffold components → 2⁵ = 32 configurations, full factorial. Found sign-flipping interactions; stopped at attribution on toy tasks.
- **Claw-SWE-Bench** (arXiv:2606.12344): fix everything except the treatment (prompt, budget, container, evaluator) so differences are attributable. Bundled harness, single runs, no inference.
- **Towards a Science of AI Agent Reliability** (arXiv:2602.16666): outcomes as distributions over K repeated runs (consistency, calibration, robustness), not scalar accuracy. Scaffold never varied.

Prior-art register — scope every claim against this (goes verbatim into DATASHEET.md):
- Harness-Bench (2605.27922): bundled harness configs × models factorial, single runs, LLM-judged process scores; explicitly disclaims causal decomposition.
- Agent Arena (arena.ai, 6/2026): randomized components on live traffic with IPW marginal effects vs a uniform baseline — the estimand CCI's sign-flips break; K=1 (models only) today; no repeats, heterogeneity, or policy.
- AHE (2604.25850): harness optimization by LLM evolution; OFAT ablations that observe but cannot identify interactions.
- 2606.09774: Resolution-IV fractional factorial over agent components, single domain.

Our unclaimed territory: **conditional component effects τ_s(C, Z) with interaction structure and simultaneous inference; repeated-seed distributional outcomes; mediation via trace features; constrained configuration policy with LOFO validation; reproducible self-hosted open weights.** This platform produces the dataset that makes that analysis identifiable. Estimation itself (DoubleML etc.) is a downstream consumer — build the data contract for it, not the estimators.

## 1. Operating rules (govern every session)

1. **Two execution sites, GitHub is the only bus.** LOCAL (this Mac + you): all code, configs, tests, docs. JUPITER (Slurm `booster`, 4× GH200 96 GB/node, 12 h walltime, AArch64, **no internet on compute nodes**, internet on login nodes, outgoing SSH blocked → git over https+token): all GPU execution.
2. **You never run GPU work.** You emit scripts and sbatch files; I run them on JUPITER and paste back errors or push results. Optional ssh mode: if I explicitly say "jupiter ControlMaster is up", you may run *read-only* commands (`ssh jupiter 'squeue -u $USER'`, `git -C ... pull`, `ls`, `cat` logs). You NEVER run `sbatch`, `scancel`, or anything mutating over ssh without my explicit go for that specific command.
3. **Results contract.** JUPITER commits ONLY: aggregated parquet/CSV panels, per-cell metric tables, `manifest.json` files, run logs ≤200 lines. Raw rollout JSONL (prompts/completions/trajectories) lives on `$SCRATCH` (90-day purge; archive script to `$DATA`), never in git. Enforce with a pre-commit size guard: reject commits adding >20 MB or any file matching `**/rollouts/*.jsonl`.
4. **Manifests.** Every job writes `manifest.json`: git SHA, experiment-config hash, model HF repo+revision SHA, vLLM version, sampling params, component-template hashes, node list, timestamps. A panel row that can't resolve to a manifest is a bug.
5. **pytest green before any sbatch is emitted as "ready".**
6. **Never destructive.** No `rm` of tracked content, no history rewrites. Migration is `git mv` + tags.
7. Tooling: Python ≥3.11, `uv` for envs, `pyproject.toml`, `ruff` + `pytest`. Conventional commits, one logical change per commit. Secrets only via `.env` (gitignored) — Blablador key, HF token.

## 2. Phase M — Migration (do this first; STOP at the end)

1. Inventory: report the current repo tree (depth 3), open TODOs, and anything referencing the HAL re-analysis pipeline.
2. Safety points: tag `pre-harnesslab`, create branch `legacy-hal` at HEAD.
3. On `main`: `git mv` all existing HAL-re-analysis material into `legacy/hal-reanalysis/` with a README stating: *this is the observational arm (HAL traces, Estimand #1: reasoning effort; Terminal-Bench fusion); it will be revived in the data-fusion phase after the factorial MVP; do not delete.* Carry forward for reuse: any `column_roles.yaml` concept, `.gitignore`, size-guard hooks, JUPITER env notes.
4. Install this document as `CLAUDE.md` at repo root. Create the skeleton of §3.
5. STOP — show me the inventory, the migration diff summary, and the new tree. I approve before Phase 0.

## 3. Target layout

```
HarnessDML/
├── CLAUDE.md                  # this file
├── ESTIMANDS.md               # written in Phase 0
├── DATASHEET.md               # written in Phase 6
├── pyproject.toml
├── harnesslab/
│   ├── components/            # one file per component + compose()
│   ├── agent/loop.py          # fixed ReAct-style loop (the Claw "base")
│   ├── tools/                 # hotpot/musique docstore, gsm8k/math calculator
│   ├── client/                # async OpenAI-compatible client (vLLM, Blablador)
│   ├── graders/               # qa_f1_em.py, numeric.py, math_sympy.py
│   ├── metrics/               # consistency, calibration, cost
│   ├── store/                 # idempotent resumable rollout store
│   ├── schedule.py            # seeded random interleaving of (config,task,seed)
│   └── cli.py                 # run | budget | status | aggregate | verify
├── configs/
│   ├── models.yaml            # tiered registry (§6)
│   ├── experiments/           # pilot.yaml, mvp_grid.yaml, arms/*.yaml
│   └── tasks/                 # committed task-ID lists per (benchmark, band)
├── schema/column_roles.yaml
├── slurm/                     # generated sbatch templates
├── scripts/hpc/               # setup_env.sh, prefetch_models.sh, serve_*.sh, archive_rollouts.sh
├── analysis/                  # thin notebooks + descriptive-ladder module (no DML here)
├── results/                   # ONLY contract-compliant artifacts, committed from login node
├── legacy/hal-reanalysis/     # preserved observational arm
└── tests/
```

## 4. Experimental design

### 4.1 Treatments
Five binary components, reconstructed faithfully from CCI §3.1/App. D (content described there, not verbatim — reconstruct, then **freeze**: content-hash every template file; hashes go in manifests):
P Planning (decompose into sub-goals) · T Tool Use (tool definitions + calling syntax) · M Memory (structured scratchpad of confirmed facts/searched entities/gaps) · SR Structured Reasoning (per-step Evidence → Gap → Reasoning → Next step) · R Reflection (post-step self-check).
Configuration = subset of {P,T,M,SR,R} → 32 cells. Secondary arms (not fully crossed): `ordering_id` (3 fixed orderings, subset of configs), `template_id` (3 paraphrase variants, 3 configs × 50 tasks).

### 4.2 Deliberate deviations from CCI (document in README; they are fixes)
1. **Submission decoupled from T.** Every config, including Bare, gets a universal final-line instruction `Answer: <answer>`. Small **bridge arm** with CCI-style coupling (submission inside T) on one model×benchmark for reconciliation.
2. **Textual tool protocol only** — `Search[q]`, `Lookup[k]`, `Calculate[e]` parsed by one strict shared regex; single retry on parse failure, event-logged. No native function calling (would confound family with interface).
3. **Hermetic benchmarks.** HotpotQA distractor: Search/Lookup over the 10 shipped paragraphs (ReAct docstore semantics). MuSiQue: same over its ~20 paragraphs. Math: sandboxed `Calculate` (asteval/sympy, no `eval`). Nothing touches the network on compute nodes.
4. **Chat-template policy.** Native tokenizer chat template per model; families without a system role get one documented fallback (prepend to first user turn); record `system_role_mode ∈ {native, prepended}` per rollout.

### 4.3 Confounding & attribution controls (engineered, not assumed)
1. **Randomized execution schedule** (`schedule.py`): within each job, the rollout queue is a seeded random interleaving over (config, task, seed) — never contiguous per config. Log node, timestamp, server-uptime per rollout.
2. **Cache & cost units.** vLLM automatic prefix caching ON (within-trajectory reuse is legitimate incremental decoding); wall-clock is diagnostic only. Primary cost outcomes: input/output **tokens**, **characters** (tokenizer-invariant, required cross-family), **GPU-seconds**. Cache stats logged as billing diagnostics, never capability.
3. **Length-matched padding control arm** (CCI §7.1): meaningless-padding pseudo-components vs real ones, one Tier-F model × both bands.
4. **Y decomposition everywhere:** Y (primary), P(answered) (was `Answer:` parseable — effects here are grader-interface effects), success|answered (cautious: conditions on post-treatment). `finish_reason=no_answer` distinguishable from wrong.
5. **C_res both conditional-on-success and unconditional.**
6. **Moderator caveat (verbatim in DATASHEET):** contrasts across family/scale/band are observational comparisons of bundled packages (capability ⊗ post-training vintage ⊗ tokenizer ⊗ template delivery ⊗ contamination). Within-generation pairs and the difficulty gate mitigate; nothing eliminates.

### 4.4 Benchmarks, bands, gate
Two families × two difficulty bands, all offline, N = 100 fixed questions per (benchmark, band), seeded sample with IDs committed under `configs/tasks/`:
- Multi-hop QA: easy **HotpotQA** (distractor) / hard **MuSiQue-Ans** — token-F1 + EM.
- Math: easy **GSM8K** / hard **MATH levels 4–5** — EM.
Step cap 4 (easy) / 6 (hard); max new tokens 256 / 512 per step; hard wall-clock timeout; all caps logged.
**Difficulty gate:** pilot measures Bare- and T-config accuracy per (model, band); a (model, family) cell enters the grid only in the band landing in **[0.15, 0.85]**; outside both → reported and dropped. Easy band retained on frontier models as a thin 4-config arm (adjudicates capability-saturation vs task-ceiling).

### 4.5 Grading spec (deterministic, program-only — NO LLM judge anywhere in Y)
- Grader scores only the extracted `Answer:` line. Missing/unparseable ⇒ 0 with `finish_reason=no_answer`.
- HotpotQA/MuSiQue: SQuAD normalization (lowercase, strip articles+punct), token-F1 + EM, max over MuSiQue aliases. Unit-test against official eval-script fixtures.
- GSM8K: numeric equality vs `#### n` gold after normalization (commas, $, units, trailing .0).
- MATH: sympy canonicalization + symbolic equivalence; string-match fallback with `grader_path` logged; heaviest test fixtures (known-equivalent and known-distinct pairs). If brittle in pilot → switch hard math band to an integer-answer AIME-style set, accept smaller N.
- Rationale (into DATASHEET): an LLM judge makes Y-error *differential in treatment* (verbose SR/R styles sway judges) — poison for component effects.

### 4.6 Seeds, temperature
Primary: temp 0.1, top-p 0.9, **K = 5 seeds/cell** (per-request `SamplingParams(seed=...)`); K = 10 for headline cells (Bare, T, T+SR+R, All-In) on the Claw-anchor Tier-F backbones and Tier B. Sensitivity arm: temp 0.0, K = 3, one Tier-F model. Cell = (model, benchmark, config, ordering_id, template_id, temp); rollout = (cell, task, seed).

## 5. Outcomes & data contract

**Per-rollout JSONL (SCRATCH):** run_id, cell fields, task_id, seed, y (F1/EM), n_turns, action list (types+order), tool_calls, parse_failures, tokens_in/out, chars_in/out, wall_s, per-call latencies, finish_reason, confidence, confidence_source, system_role_mode, node, ts, manifest_ref.
**Confidence elicitation:** after `Answer:`, one extra turn — "rate your confidence 0–100, respond with ONLY a number"; fallback heuristic sets `confidence_source=fallback`.
**Per-cell metrics** (unit-tested vs hand-computed fixtures): C_out = mean_t(2p̂_t−1)²; trajectory consistency C^d (1 − mean pairwise JSD over action-type distributions) and C^s (1 − mean normalized Levenshtein over action sequences); C_res = exp(−mean CV) over {tokens_out, wall_s, tool_calls}, conditional AND unconditional; pass@k and pass∧k; ECE (10 bins), AUROC, Brier; cost aggregates in tokens/chars/GPU-seconds.
**schema/column_roles.yaml** tags every column: `treatment` (P,T,M,SR,R, ordering_id, template_id) | `context` (model_family, model_scale, benchmark, band, temp, system_role_mode) | `pre_treatment` (task_id, item features, held-out difficulty from a disjoint calibration slice only) | `outcome` | `post_treatment` (turns, tokens, tool_calls, parse_failures, trajectory features — mediators, never controls). `load_panel(role_filter=...)` **hard-errors** if a post_treatment column is requested as covariate.
**Generalization scope (governs every REPORT):** model/family/scale/band/template are fixed factors; inference is conditional on the tested grid; no claims about untested or future models; the only cross-environment statements are empirical **LOFO** and leave-one-band-out splits (aggregate emits split indices); new-model onboarding is a procedure (pilot + gate + 4 headline configs ≈ 2k rollouts, then partial pooling as shrinkage, never superpopulation inference).
**Deliverables per experiment** (committed from login node): `results/<exp_id>/panel.parquet` (rollout-level, no text), `cell_metrics.parquet`, `manifest_index.json`, `REPORT.md` (auto-generated: counts, failure rates, throughput, CCI-comparison tables — T dominance? All-In loss? sign-flip replication across families? — plus Y-decomposition table). Descriptive ladder only in `analysis/`: naive cell means → task-FE OLS with task-clustered SEs → per-component marginals stratified by (family, band). Export tidy DoubleML-ready frames. **No DML estimation in this repo phase.**

## 6. Model registry (`configs/models.yaml`) — frontier-first

Fields: hf_id, revision (pinned after prefetch), family, total/active params, tier, serving_mode, license note. Entries marked (verify) resolve on the login node before download; substitute within-family if gated — never silently. Implement `fits-check` (params × dtype vs 4×96 GB/node) assigning serving_mode.

| Tier | Model | Serving | Note |
|---|---|---|---|
| F | latest GLM-5.x (`zai-org/GLM-5.1`+, verify) | 1 node | Claw claw-sweep anchor |
| F | Qwen 3.6-flash or largest Qwen fitting 1 node (verify) | 1 GPU–1 node | Claw anchor |
| F | `deepseek-ai/DeepSeek-V4-Flash` (verify) | 1 node | Claw model-sweep backbone |
| F | `meta-llama/Llama-4-Scout-17B-16E-Instruct` | 1 node BF16 TP=4 | current open Llama |
| F | Mistral Medium 3.5 / Small 4 — largest fitting 1 node (verify) | 1 GPU–1 node | current open Mistral |
| F | `openai/gpt-oss-120b` | 1 node | distinct post-training lineage |
| F/G opt | latest Gemma (verify) | 1 GPU–1 node | exercises no-system-role fallback |
| G | Seed 2.0-mini (verify) · `openai/gpt-oss-20b` · smallest current Qwen/Mistral (verify) | 1 GPU | weak pole + within-family gradient pairs |
| B | `meta-llama/Llama-3.1-8B-Instruct` | 1 GPU | bridge arm ONLY (CCI's validated cell) |
| S | DeepSeek-V4-Pro, Mistral Large 3, Llama-4-Maverick, Kimi K2.6 (verify) | multi-node | headline cells only — **out of MVP scope** |

Rationale to preserve in comments: Claw-roster alignment enables the composition check of our component effects against their bundled harness gaps on identical backbones; capability moderation comes from within-generation G-vs-F pairs (cross-generation confounds capability with post-training vintage); Tier B validates the re-implemented instrument before trusting Tier-F divergences.

## 7. JUPITER execution

- Env: `scripts/hpc/setup_env.sh` — sc_venv_template base, `module load Stages/2025 GCC Python CUDA`, **vLLM built from source on AArch64** (SDLAML guide; `VLLM_TARGET_DEVICE=cuda`, `--no-build-isolation`), idempotent.
- Prefetch (login node only): `prefetch_models.sh` — `HF_HOME=$SCRATCH/hf`, download registry entries, write back revision SHAs. Compute runs `HF_HUB_OFFLINE=1`.
- Serving per node: fits-one-GPU → 4 independent vLLM servers (CUDA_VISIBLE_DEVICES=i, ports 8001–8004); fits-one-node → one server `--tensor-parallel-size 4`. Health-check loop before clients start.
- Slurm: array jobs over (model × benchmark band), `--partition=booster --gres=gpu:4 --time=11:30:00`, launch with `srun` (never mpiexec). Rollouts stream to `$SCRATCH/harnesslab/<exp_id>/rollouts/`; `aggregate` runs as `--dependency=afterok`; results committed manually from a login node.
- Resume by construction: rollout store keys `hash(cell, task_id, seed)`; completed keys skipped; re-submission of finished work is a no-op.
- `harnesslab budget <exp.yaml>`: prints rollouts, token estimates, node-hours from measured pilot throughput; **refuses to emit sbatch for any experiment lacking a pilot-throughput constant**. (Planning anchor: MVP ≈ 30–70 node-hours total.)

## 8. Tests (all local, mock backend; required before Phase 3)

1. Golden files: exact composed system prompt for 32 configs × 3 orderings × 3 templates × 2 benchmarks. 2. Parser: action grammar, malformed actions, retry-once, `Answer:` edge cases. 3. Tools: docstore determinism; calculator sandbox rejects imports/attribute access. 4. Graders: official-fixture parity (QA), numeric normalization table, sympy equivalent/distinct pairs. 5. Metrics: C_out, JSD, Levenshtein, C_res, ECE, AUROC, Brier vs hand-computed fixtures; pass@k/pass∧k identities. 6. Store: idempotency; partial-line corruption survives resume. 7. Schedule: interleaving property (no config runs contiguously beyond chance). 8. Size guard rejects an oversized fake commit. 9. `load_panel` hard-errors on post_treatment-as-covariate.

## 9. Phases (one per chunk; STOP at each)

- **Phase M — Migration** (§2). STOP.
- **Phase 0 — Skeleton, schemas, ESTIMANDS.md.** Layout, pyproject, models.yaml, column_roles.yaml, panel schema, size guard, and `ESTIMANDS.md`: primary estimands (per-component conditional effects by (family, band); interaction structure; Y-decomposition rules; fixed-factor scope; simultaneous-inference/best-arm plan for "best config" claims — naive argmax of 32 cells is winner's-cursed). STOP: I review schemas + estimands before any logic.
- **Phase 1 — Components, loop, tools, graders, mock client, full test suite.** STOP when pytest green; show the golden prompt for T+SR+R on HotpotQA and the grader fixture report.
- **Phase 2 — Live smoke via Blablador** (`https://helmholtz-blablador.fz-juelich.de`, OpenAI-compatible, key in `.env`) or any local endpoint: 2 configs × 5 tasks × 2 seeds end-to-end → JSONL → aggregate → mini-REPORT. STOP.
- **Phase 3 — JUPITER provisioning.** setup_env.sh, prefetch_models.sh, serving launchers, sbatch templates, budget command. STOP: I run on the login node and paste errors back.
- **Phase 4 — Pilot.** `pilot.yaml` = 4 configs × 20 tasks × 2 seeds × (one Tier F + one Tier G) × all four bands; doubles as the **difficulty-gate measurement**. After I run and push: verify panels, compute throughput constants, write band assignments into the grid config. STOP.
- **Phase 5 — MVP grid.** Full Tier F+G on gated bands; bridge arm (Tier B) alongside; padding/ordering/template/temp-0 arms per §4. Emit arrays; monitor via `status`; aggregate; REPORT with CCI-comparison + Claw-composition tables. STOP.
- **Phase 6 — Freeze & handoff.** Panel v1.0; `DATASHEET.md` (design, deviations, confounding controls, moderator caveat, prior-art register, onboarding recipe); DoubleML-ready frames + LOFO/band split indices. Tag `mvp-v1.0`. STOP.

Post-MVP pointers (out of scope now, do not build): task-family expansion (code-with-tests → ALFWorld/WebShop → Apptainer'd SWE slice → Harness-Bench suite with completion-only Y), Tier S giants, HAL/Terminal-Bench observational fusion reviving `legacy/hal-reanalysis/`.

## 10. Non-negotiables

Components are the ONLY thing varying within (model, band). Execution order is randomized within jobs. Every rollout resolves to a manifest. Post-treatment columns are never controls. No LLM judge touches Y. Raw text never enters git. pytest before sbatch; pilot before grid; gate before full band. Fixed-factor language only — no transport claims. When uncertain: stop and ask, in one short question, with your recommended default.
