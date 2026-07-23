# Exploration: `taubench_airline` slice (run 20260723T085732Z-b4a1bb2b)

Analyzed locally from `results/explore/taubench_airline/{runs,aggregate}.json` +
`schema/SCHEMA.md` only. 47 runs × 50 shared tasks = **2,350 rollouts**, 3.17 GB decrypted.

## Trace anatomy (identical across all 47 runs)

| top-level key | type | content |
|---|---|---|
| `config` | dict | run_id, benchmark_name, agent_name, date, run_command, `agent_args{model_name, reasoning_effort?, budget?, temperature?, provider?}` |
| `results` | dict | `accuracy`, `total_cost`, `successful_tasks[]`, `latencies{task→ first/last ts, total_time}` |
| `raw_eval_results` | dict | one entry per task `"0".."49"`: `{reward, taken_actions[], task{instruction, user_id, actions[]}}` — or an `"ERROR: …"` string on harness failure |
| `raw_logging_results` | list | 1,375–2,652 per run (87,622 total): one `{call_id: record}` per LLM call with `model`, `usage`, `choices[]`, `weave{status, latency_ms}`, **`weave_task_id`** |
| `total_usage` | dict | per-model token totals — **includes the user-simulator model** |
| `total_cost` | float | duplicate of `results.total_cost` |
| `git_info` | dict | harness commit/branch (42/47) |

Load-bearing facts: every LLM call carries `weave_task_id` → per-rollout
tokens/calls/cost are reconstructable; `results.latencies` gives per-rollout
wall-clock; task instructions are embedded → `task_prompt_len` is derivable;
all runs share the same 50 tasks → within-task contrasts everywhere.

## The design (scaffold × model × reasoning)

Scaffolds: `hal_generalist_agent` (16 runs), `taubench_few_shot` (19),
`taubench_tool_calling` (12). Models: 13 canonical (incl. off-paper gpt-4o,
o3-mini, o3-preview-0403). Reasoning: `high` 15 / `low` 4 / `medium` 2 /
`minimal` 2 / unset ("default") 24.

**Estimand-1 contrast pairs (same scaffold, same model, same provider route, 1 run per arm):**

| scaffold | model | contrast | acc |
|---|---|---|---|
| generalist | claude-3.7-sonnet | default → high | 0.56 → 0.44 |
| generalist | claude-opus-4 | default → high | 0.44 → 0.44 |
| generalist | claude-opus-4.1 | default → high | 0.54 → 0.32 |
| generalist | gpt-5 | minimal → high | 0.38 → 0.30 |
| generalist | o4-mini | low → high | 0.22 → 0.18 |
| fewshot | claude-3.7-sonnet | default → high | 0.34 → 0.60 |
| fewshot | claude-opus-4 | default → high | 0.56 → 0.66 |
| fewshot | claude-opus-4.1 | default → high | 0.54 → 0.62 |
| fewshot | gpt-5 | minimal → high | 0.50 → 0.52 |
| fewshot | o3-mini | default/low → high | 0.48/0.40 → 0.40 |
| fewshot | o4-mini | low → high | 0.48 → 0.60 |
| toolcalling | claude-3.7-sonnet | default → high | 0.44 → 0.52 |
| toolcalling | claude-opus-4.1 | default → high | 0.50 → 0.52 |
| toolcalling | o4-mini | low → high | 0.36 → 0.56 |

Naive reading: **on `hal_generalist_agent` more reasoning uniformly hurts; on the
two TAU-bench-native scaffolds it mostly helps.** A scaffold×reasoning
interaction, invisible in pooled numbers, is the first genuinely interesting
GATE target — and exactly what the paper's per-setting counting cannot weigh.

Support caveats: one run per arm → within a pair, inference lives entirely on
50 paired task outcomes; the shared task set gives 50 clusters overall.
Anthropic "extended thinking" is recorded uniformly as `reasoning_effort:
high`; "default" for o-series means provider-default (≈medium) — label
contrasts honestly as *explicit-X vs provider-default*.

## Task difficulty spread (cross-run solve rates, 47 runs)

Task 25: 0/47 solved; task 19: 1/47; task 2: 1/46 … task 42: 41/47; task 38:
36/47. Strong, stable spread → the leave-one-config-out difficulty covariate
will carry real signal, and within-task contrasts absorb it entirely.

## Quality flags (full list: discrepancies.md)

13/2,000 task-entries are harness ERROR strings (~0.65%); `total_cost` may
include gpt-4o user-simulator spend (verify by price reconstruction);
reward dtype drifts (float/int); harness commit varies across runs (10
commits, 2 repos); off-paper models present.

## Verdict on prompt assumptions

Confirmed: encrypted zips → one JSON per run; Weave call trees with tokens and
costs; success from benchmark's scored field (`reward`); ~50-task rollout unit.
Corrected: reasoning treatment lives in `config.agent_args` (not per-rollout);
cost is run-level (per-rollout cost must be derived); scaffold identity comes
from `run_command`, not `agent_name` (46 distinct strings).
