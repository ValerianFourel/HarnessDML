# Progress journal

Everything below happened on **2026-07-23** (one long build day, local Mac +
JUPITER login nodes). Newest state at the bottom.

## Where this repo came from

The repository previously hosted the **HAL observational arm**: a Double-ML
causal re-analysis of the Holistic Agent Leaderboard traces (2,350 TAU-bench
rollouts explored end-to-end; empirical schema + field mapping drafted). Its
headline exploratory finding — reasoning effort *hurts* on HAL's generalist
scaffold but *helps* on TAU-bench-native scaffolds — is precisely the kind of
scaffold×treatment interaction HarnessLab is built to identify by design
rather than observationally. That arm is preserved, runnable, and paused in
[`legacy/hal-reanalysis/`](../legacy/hal-reanalysis/) (branch `legacy-hal`,
tag `pre-harnesslab`); it returns in the post-MVP data-fusion phase.

## Phase M — migration (`4dd03f9`…`a8ec2d6`)

Tagged `pre-harnesslab`, branched `legacy-hal`, `git mv`-ed the entire HAL
pipeline (41 files, zero deletions) into `legacy/hal-reanalysis/`, installed
the HarnessLab spec as `CLAUDE.md`, scaffolded the target layout.

## Phase 0 — schemas & estimands (`e070991`…`1c61352`)

- `schema/panel_schema.yaml`: the 47-column rollout contract + cell-metrics table.
- `schema/column_roles.yaml`: every column gets one causal role; post-treatment
  is never a covariate (hard error, tested).
- `configs/models.yaml` v0 (spec's table, verify flags), pre-commit size guard
  (>20 MB / `rollouts/*.jsonl`), `ESTIMANDS.md` (uniform-factorial component
  effects, interaction/sign-flip register with simultaneous coverage,
  Y-decomposition, task-clustered inference, MCB + seed-split best-arm
  protocol, fixed-factor scope).

## Phase 1 — the library (`bb2c0d8`)

Components (5 × 3 templates × 3 orderings, frozen via 576 golden hashes,
padding + bridge arms), strict protocol + fixed ReAct loop, hermetic
docstore/calculator, deterministic graders with parity fixtures, consistency/
calibration metrics vs hand-computed values, resumable corrupt-tail-safe
store, seeded interleaving, schema-exact runner, aggregate → panel/metrics/
REPORT, CLI. 106 tests at the time (114 now). Caught a real store bug in
testing (append could glue onto a truncated line).

## Phase 3 — JUPITER provisioning (`e007d9c`…`01b3955`)

Built before the smoke finished, so the cluster was never blocked:
`setup_env.sh` (AArch64 vLLM wheel-or-source), prefetch with revision
pinning to a lock file, `serve_node.sh` (4 replicas vs TP=4, health loop),
sbatch templates (later: multi-benchmark sequential mode, `69d84d9`),
`fits-check`, `MultiEndpointClient`, CLI `--set` overrides, seeded task-list
builder. Task lists for all four benchmarks were built ON the login node and
committed (`0dce3d8`): hotpotqa (pool 7405), musique (2417), gsm8k (1319),
math levels 4–5 (262) — 100 each, zero skips.

**Registry resolved against the live hub** (`01b3955`): GLM-5.x is 753B in
every variant → Tier S, the Claw GLM anchor is out of the MVP;
DeepSeek-V4-Flash (158B) fits one node only as native FP8 (dtype added to
fits-check); no open Mistral Medium exists → Small-3.2-24B / Ministral-3-3B;
Qwen → 3.6-27B with a cross-vintage 3.5-9B pole; gemma-4 26B-A4B/E4B is the
one clean within-generation pair; "Seed 2.0-mini" doesn't exist → parked.
gpt-oss-120b/20b prefetched to `$SCRATCH/hf` and revision-locked (`adb0040`).

## Phase 2 — live smoke: incident log (in progress)

| job | outcome | lesson → fix |
|---|---|---|
| 1025300 | FAILED 11 s — `libpython3.12.so.1.0` missing | venv links against module python; batch env had no modules → `scripts/hpc/env.sh`, sourced by every shell and sbatch (`ae52405`) |
| 1025480 | doomed, cancelled — prefetch had failed silently | JUPITER has no `$SCRATCH` until jutil; only `$SCRATCH_<project>` → env.sh auto-resolves (`21e5622`) |
| 1025599 | COMPLETED 19 min — servers healthy, 20/20 rollouts ran, **but every request 404'd**: client asked vLLM for the registry key, vLLM serves the `hf_id`; the api_error rows were persisted as *done*, blocking resume | client now resolves `served_model_name()` from the registry; api_error rollouts go to `failures.jsonl`, stay pending, retried on resume; `run` exits 3 on any api_error (`e15c6b3`) |
| 1028919, 1029025 | COMPLETED but no-ops — ran before the poisoned store was moved aside; skipped 20 "done" rows, did nothing | store `mv`'d to `smoke_live_bad_1025599`; exactly the failure mode `e15c6b3` prevents from here on |
| 1029055 | FAILED — first clean-store run with the 404 fix: servers healthy, **all 20 requests 500'd** `openai_harmony.HarmonyError: error downloading or loading vocab file`. vLLM renders gpt-oss chats through openai_harmony, which fetches its tiktoken vocab from the internet on *first request* (never at load, so `/health` passes) — compute nodes are offline. Guardrail worked: nothing persisted, store stayed resumable | first fix (`fdba039`): warm a `TIKTOKEN_RS_CACHE_DIR` cache on a login node — **superseded below**, the warm-up itself failed |
| (login shell) + 1029364 | the cache warm-up threw the same HarmonyError **on the login node** — harmony's Rust downloader can't reach the Azure blob from JUPITER at all (the same URL took ~3 min to download from a laptop; harmony gives up). 1029364 then died fast on the new exit-5 guard — the guard doing its job | the vocab (3.6 MB) is now **vendored in-repo** at `assets/harmony-vocab/o200k_base.tiktoken`, sha256-verified against harmony's own pin (`446a9538…`); `env.sh` exports `TIKTOKEN_ENCODINGS_BASE` at it, so harmony reads disk and never touches the network on any node; `prefetch_models.py` verifies existence+hash; guard now checks the file |

**Job 1029480: GREEN** — `ran=20 api_errors=0`, 0 corrupt lines, resume
machinery proven on the exact 20 rollouts 1029055 had quarantined.

## Phase 2 — review verdict (STOP passed)

The panel told a real story on first contact: BARE answered 8/10 vs T 5/10,
with success|answered = 100 % for both — the whole gap is P(answered). All 7
`no_answer` rows had `chars_out = 0`: gpt-oss emits its reasoning into the
hidden harmony channel and (4/7 at exactly the 2×256-token ceiling) died
there without one visible character. Y-decomposition working as designed;
grader, metrics, REPORT all correct.

Review found three gaps, fixed pre-pilot (approved: "all 3 fixes, then
pilot"):
1. `git.sha=unknown` in the manifest (no git binary on compute nodes; also
   silently claimed `dirty=false`) → pure-Python `.git/HEAD` fallback,
   `dirty=null` when unverifiable.
2. Manifest lacked `hf_id`, pinned revision, vLLM version (§1.4 requires
   all three) → spec carries hf_id+revision from the registry; client_info
   records the venv's vLLM version.
3. Hidden-channel cost was invisible → new panel column
   `chars_out_reasoning` (48 columns now) + `chars_out_reasoning_mean` in
   cell metrics; `chars_out` stays visible-only. NOTE: stores written
   before this change (the smoke store on `$SCRATCH`) will fail aggregate's
   schema check — committed smoke results stay valid; don't re-aggregate
   the old store; pilot stores are fresh.

## Phase 4 — pilot (in progress)

Submitted 1029740 (120b) + 1029741 (20b). **Incident:** the submit script
passed `--export=ALL,...,BENCH=hotpotqa,musique,gsm8k,math` — `--export`
splits on commas, so Slurm truncated `BENCH` to `hotpotqa` and treated the
other three benchmarks as unrelated variable names. 1029741 COMPLETED in
4:10 with hotpotqa only — but that slice is fully green (160/160,
api_errors=0, first pilot data in hand). Fix: submit via env prefix
(`EXP=… MODEL_ID=… BENCH=… sbatch …`; sbatch propagates the submission env
by default); sbatch template additionally accepts `+` as a separator for
--export users. Remainder jobs (musique,gsm8k,math × both models) submitted
as separate jobs — per-slice stores make that safe.

Then: difficulty gate + throughput constants from the 8 slices.

## 2026-07-24 — probe verdict: gpt-oss × textual protocol incompatibility

20b slices landed green (hotpotqa 160, musique 160, gsm8k 158+2 pending);
20b math never ran (a transient-api-error exit aborted the job under
`set -e` — sbatch loop now continues past a failing bench). Both 120b jobs
died at the 40-min health ceiling: vLLM **engine core failed at init**
(root cause still to extract from the server log).

Probe job 1033971 (raw responses, instrument's exact prompts) explained the
hotpotqa disaster: **BARE** ends `finish_reason=length` with `content=null`
at 256 AND 1024 tokens — everything goes to the hidden harmony reasoning
channel, the visible final message never starts; **T** ends
`stop_reason=200012` (harmony `<|call|>`) — the model attempts a *native*
tool call instead of the textual `Action:` line, at just 92/1024 tokens.
`include_reasoning=false` hides the channel without producing content.
`reasoning_effort=low` shortens reasoning but doesn't rescue either mode.
Not a code bug: a family×interface incompatibility (ADR 16 institutes
probe-before-pilot per family).

Decision (user): parallel-track. (1) Prefetch + probe Mistral-Small-3.2-24B
(F) and Qwen3.5-9B (G), pilot on what passes; (2) one gpt-oss rescue probe
(2048 budget + low effort + the loop's exact retry nudge) decides keep vs
drop; (3) extract the 120b engine-init root cause. Also fixed: vLLM renamed
`reasoning_content`→`reasoning`, so `chars_out_reasoning` was silently 0 —
client reads both now.

## Next

1. Green smoke → "pull and review smoke" (Phase-2 STOP).
2. `bash scripts/hpc/submit_pilot.sh` — 2 parallel nodes (gpt-oss-120b/20b ×
   all four bands); yields the difficulty gate and throughput constants
   (unlocks `harnesslab budget`).
3. Prefetch + gate-jobs for the resolved roster; request meta-llama hub
   access (Scout + 3.1-8B bridge).
4. Phase 5 MVP grid: per gated (model, band) 32 configs × 100 tasks × 5 seeds
   (+K=10 headline top-ups) + bridge/padding/ordering/template/temp-0 arms.
5. Phase 6: panel v1.0, DATASHEET.md, tag `mvp-v1.0`.
