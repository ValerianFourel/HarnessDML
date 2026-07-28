# Data inventory — what the ~4.1M rollouts actually are

Snapshot: **2026-07-28**, from `harnesslab progress --deep --roster`. Numbers
are *unique in-scope* rollouts (out-of-scope orphans and re-key duplicates
excluded — see §6). Re-generate any figure here with:

```sh
python -m harnesslab.cli progress --deep --roster
```

---

## 1. One line each

* **~4.09M** census rollouts — the 2⁵ factorial (32 configs) × task × 5 seeds,
  on 9 models across 4 benchmarks. 43.6% of the 9.37M the full gate matrix
  asks for.
* **~44.6k** non-census rollouts — the control arms, the CCI bridge pair, the
  K=10 headline arm, and every pilot.
* **~4.75M** rollouts were actually executed; the difference is orphans and
  duplicates, both explained in §6 and both dropped at harvest.
* **Three models are complete**: qwen_3_5_9b (all four bands), ministral_3_3b
  (both gated bands), mistral_small_3_2_24b (98.8%, 11.5k rollouts short).

## 2. The census — 2⁵ factorial per (model, band)

Every cell is (model, benchmark, config, ordering=o1, template=t1, padding=∅,
temp=0.1) × task × seed∈{0..4}. Targets are configs × in-scope tasks × seeds:
hotpotqa 3000 tasks → 480,000; musique 2417 → 386,720; gsm8k 1319 → 211,040;
MATH L4-5 262 → 41,920.

| model | tier | hotpotqa | musique | gsm8k | math | total |
|---|---|---:|---:|---:|---:|---:|
| qwen_3_5_9b | G | 480,000 ✅ | 386,720 ✅ | 211,040 ✅ | 41,920 ✅ | **1,119,680** |
| mistral_small_3_2_24b | F | 468,433 | 386,720 ✅ | 26,380 ✅ ᵗʰⁱⁿ | 41,919 | **923,452** |
| ministral_3_3b | G | — dropped | 386,720 ✅ | 211,040 ✅ | — dropped | **597,760** |
| gemma_4_26b_a4b | F | 267,860 | 0 | 169,985 | 41,920 ✅ | **479,765** |
| gemma_4_e4b | G | 0 | 222,755 | 211,040 ✅ | 41,920 ✅ | **475,715** |
| qwen_3_6_27b | F | 118,892 | 58,675 | 87,163 | 41,294 | **306,024** |
| kimi_linear_48b | F | 42,640 | 31,284 | 0 | 0 | **73,924** |
| llama_4_scout | F | 23,828 | 13,819 | 18,461 | 8,196 | **64,304** |
| qwen_3_5_122b | F | 19,979 | 10,477 | 14,328 | 0 | **44,784** |

✅ = slice complete. `mistral × gsm8k` is the 4-config **thin arm** (BARE .875
saturates the [0.15, 0.85] window, ADR 18), not a hole in the factorial.
Blank cells are gated-in but unstarted; `ministral × {hotpotqa, math}` failed
the gate and is deliberately absent.

**Complete slices are what analysis can use today**: 8 fully saturated
(model, band) factorials — 4 models × their bands — covering every one of the
32 configurations at k=5 on the whole benchmark pool. That is already the
core claim of the design: per-component conditional effects with interaction
structure, estimated within (model, band), on a *census* rather than a sample
of each benchmark.

## 3. The arms — what varies besides the five components

| arm | spec | model | bands | rollouts | what it identifies |
|---|---|---|---|---:|---|
| padding | `arms/padding.yaml` | mistral | hotpotqa, math | 6,000 ✅ | length-matched meaningless components vs real ones (CCI §7.1) — is an effect the component or the token count? |
| ordering | `arms/ordering.yaml` | mistral | hotpotqa | 3,000 ✅ | 3 block orderings × 3 configs — prompt-position sensitivity |
| template | `arms/template.yaml` | mistral | hotpotqa | 1,500 ✅ | 3 paraphrases × 3 configs — wording sensitivity |
| temp0 | `arms/temp0.yaml` | mistral | hotpotqa, math | 2,400 ✅ | temp 0.0, k=3 — how much of the variance is sampling |
| bridge coupled | `arms/bridge_coupled.yaml` | llama_3_1_8b | hotpotqa | 6,400 ✅ | CCI's design: submission lives *inside* the T block |
| bridge decoupled | `arms/bridge_decoupled.yaml` | llama_3_1_8b | hotpotqa | 6,400 ✅ | ours: universal `Answer:` line in all 32 configs |
| K=10 headline | `mvp_headline_topup.yaml` | mistral | hotpotqa, musique, math | 12,000 ✅ | 4 headline configs at 10 seeds — consistency/pass@k with usable SEs |

All seven are **complete and harvested**. The bridge pair is the instrument
validation: same model, same 32 configs, same 100 tasks, same 2 seeds, same
schedule seed — one field differs. If component effects agree in sign across
the two halves, the re-implementation is validated against CCI's original;
if not, that is a finding about the instrument and belongs in the DATASHEET
before any component effect is reported.

## 4. Pilots and probes — 43 slices, 6,878 rollouts

4 headline configs × 20 tasks × 2 seeds per (model, band), for all 11 models
that got past a probe. These are the **difficulty-gate measurements** (§4.4)
recorded in `configs/gates.yaml`, and they are the only place `gpt_oss_20b`
(ADR 17: T undeliverable) and `llama_3_1_8b` appear outside their arms.
`analysis/model_matrix.sh` reads them as a cross-model BARE/T/T+SR+R/All-In
table.

### Not deliverables

`smoke_live` (Phase-2 connectivity test, 20 rollouts) and any `*_bad_*`
quarantined store are skipped by `harvest_all.sh`. The smoke slice predates
`chars_out_reasoning` in the panel schema, so re-aggregating it fails the
schema check — correctly. Its Phase-2 panel stays committed as history; the
fix is never to backfill missing columns, because that would turn the schema
guard into a rubber stamp.

## 5. What one row is

`schema/panel_schema.yaml` + `schema/column_roles.yaml` are the contract; the
roles are load-bearing, not documentation. Per rollout:

* **treatment** — `comp_P/T/M/SR/R`, `ordering_id`, `template_id`,
  `padded_components`
* **context** — model family/scale, benchmark, band, temp, `system_role_mode`
* **outcome** — `y` (token-F1 or EM), `em`, `answered`, `finish_reason`,
  `confidence`
* **post_treatment** — `n_turns`, `n_tool_calls`, `n_parse_failures`,
  `tokens_in/out`, `chars_in/out`, `wall_s`, `gpu_seconds`, `action_seq`.
  Mediators and cost outcomes. `load_panel(covariates=...)` **hard-errors** if
  one is requested as a covariate.
* **meta** — `rollout_key`, `manifest_ref`, `node`, `ts_*`, `seed`,
  `grader_path`

No prompt or completion text, by contract. Trajectories survive as action-type
sequences. Every row resolves to a manifest carrying the git SHA, model repo +
pinned revision, vLLM version, sampling params, per-block template hashes and
the task-list sha256.

Grading is deterministic and program-only — SQuAD-normalized token-F1/EM for
QA, numeric equality for GSM8K, sympy canonicalization for MATH. **No LLM
judge touches Y**, because judge error would be differential in treatment
(verbose SR/R styles sway judges) and that is exactly the bias a component
factorial cannot absorb.

## 6. Known artifacts — read before analyzing

1. **Orphans (503,755 rows).** HotpotQA's pool is 7,405 tasks and the census
   was capped to the first 3,000 (ADR 20) *after* the schedule had already
   scattered work across all of them. Only hotpotqa can have these (every
   other pool is under the cap). `aggregate --task-scope auto` drops them at
   harvest; they never reach a panel.
2. **Re-key duplicates (~113,610 rows).** Adding `padded_components` to the
   cell identity changed every `rollout_key`, so each pre-padding slice re-ran
   its wave-1 tasks once — exactly 16,000 rows for a 32×100×5 slice (ADR 22).
   They are real rollouts with unique keys, so `verify` cannot see them; only
   `(cell, task, seed)` repeats, leaving 100 tasks at k=10 while the rest are
   k=5. `aggregate` always reports the count and drops them under `--dedupe`.
   **Decide this before the analysis panel is frozen.**
3. **Unequal per-cell power.** Census size is the qualifying pool, not an
   equal sample: 3,000 / 2,417 / 1,319 / 262 tasks. MATH is smallest because
   it draws from MATH-500 filtered to levels ≥ 4.
4. **Band labels are labels.** musique (hard) outscores hotpotqa (easy) on
   BARE for both wave-1 models — alias-max F1 generosity and/or
   contamination. The bands are not a verified difficulty ordering (ADR 18).
5. **Interface findings, not capability findings.** gpt-oss cannot receive T
   at all (native harmony tool calls, ADR 17). llama_3_1_8b's T collapses to
   y=0.000 on QA. llama_4_scout's hotpotqa T drops .314 → .095. Each needs
   adjudicating as instrument-vs-model before it is read as a component
   effect.

## 7. Where it lives

* **Raw rollout JSONL** — `$SCRATCH/harnesslab/<exp>/rollouts_<model>_<bench>/`,
  ~5.5 GB, never in git. **90-day purge; harvest before it bites.**
* **Panels** — `results/<exp>_<model>_<bench>/panel*.parquet` (sharded above
  300k rows, ADR 20) + `cell_metrics.parquet` + `manifest_index.json` +
  `REPORT.md`, committed.
* **Scope, estimands, decisions** — `ESTIMANDS.md`, `docs/DECISIONS.md`
  (26 ADRs), `configs/gates.yaml`, `docs/SESSION_*.md`.

## 8. Publishing to HuggingFace

`scripts/publish_hf_dataset.py` uploads `results/` + `schema/` with a
generated card. It reads nothing from `$SCRATCH`, so raw text cannot leak.

```sh
bash scripts/hpc/harvest_all.sh                    # panels current first
export HF_TOKEN=hf_...                             # write token; .env works too
python scripts/publish_hf_dataset.py --repo <user>/harnesslab-panels --dry-run
python scripts/publish_hf_dataset.py --repo <user>/harnesslab-panels
python scripts/publish_hf_dataset.py --repo <user>/harnesslab-panels --public
```

Login node only (compute nodes have no internet). Re-running is incremental.
Default is a **private** repo; `--public` is a deliberate, irreversible-ish
act — the panels carry no text, but publishing is publishing.

Consumers get:

```python
import polars as pl
panel = pl.read_parquet("hf://datasets/<user>/harnesslab-panels/slices/*/panel*.parquet")
```

and `schema/column_roles.yaml` beside it, which is the file that stops a
downstream user from conditioning on a mediator.
