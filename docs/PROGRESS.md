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

Current: smoke resubmission pending with the fix; expected green
(`ran=20 api_errors=0`), then aggregate → verify → push → local review gate.

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
