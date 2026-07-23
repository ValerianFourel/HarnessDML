# Discrepancies vs. the HAL paper / prompt assumptions

Never silently adjusted — every reconciliation decision is recorded here
(CLAUDE.md guardrail 5). Slice: `taubench_airline`, run `20260723T085732Z-b4a1bb2b`.

1. **Extra models beyond the paper's 9.** The slice contains `gpt-4o-2024-11-20`
   (1 fewshot run), `o3-mini-2025-01-31` (3 runs), and an `o3-2025-04-03`
   preview checkpoint alongside `o3-2025-04-16`. The HF repo is a superset of
   the paper's analysis set; panel rows are kept and a `in_paper_set` filter
   will be defined when we reconcile against the paper's 21,730.
2. **Reasoning effort recorded inconsistently.** Some runs annotate effort only
   in the upload FILENAME, not in config (e.g.
   `hal_generalist_agent_o320250416_medium_*` and `taubench_fewshot_o320250416_medium_*`
   have no `agent_args.reasoning_effort`), while
   `taubench_toolcalling_o320250416_*` records `medium` explicitly. Decision:
   `config` is ground truth; missing → level `default` (provider-default arm);
   filenames are annotations only. Consequence: "default" for o3/o4-class
   models factually means medium effort — contrast labels must say
   "explicit-X vs provider-default", not "X vs none".
3. **Harness errors ≈ 0.65% of rollouts.** 13 of 2,000 sampled task-entries are
   `"ERROR: <traceback>"` strings (no reward). Coded `success=0`,
   `termination_reason='harness_error'`; ETL validates against
   `results.accuracy` (does HAL count them as failures?) and reports the delta.
4. **`total_cost` may include the user simulator.** TAU-bench uses a gpt-4o
   user simulator (`gpt-4o-2024-08-06` in 40/47 runs, `openai/gpt-4o` in 7);
   its usage appears in `total_usage` and inside per-call `usage`. Whether
   `results.total_cost` includes simulator spend must be verified by
   recomputing cost from tokens × prices in ETL before any cost estimand runs.
5. **Reward dtype drift.** `reward` is `1.0/0.0` (float) in most runs, `0`
   (int) in others (predominantly toolcalling-era). Cast to int; cosmetic.
6. **Harness version varies across runs.** 10 distinct hal-harness commits
   from 2 repos (`princeton-pli`, `benediktstroebl` fork), branches
   `main`/`update-tau-bench-commit`; 5 early runs lack `git_info` entirely.
   `harness_commit` is a covariate/caveat; scaffold identity is confounded
   with harness era (toolcalling runs are all 2025-10).
7. **`budget` knob only in hal_generalist runs** with drifting placeholder
   values (9999/99999/999999/9999999). Constant within every reasoning
   contrast pair (verified), so not a within-pair confounder; recorded as a
   scaffold-config covariate.
8. **One run lacks `run_command`** (`taubench_airline_1743961943`, the gpt-4o
   fewshot run) — scaffold recovered from `agent_name` ("TAU-bench FewShot").
