# Decision log (ADR-lite)

Each entry: what we decided, and why. Reversals get a new entry, never an edit.

1. **Uniform-factorial estimand for component effects.** τ_j is the main
   effect averaged over the uniform distribution of the other four components
   — a design-measure quantity. Reported per (model, band); never pooled over
   contexts without showing strata (sign-flips are the finding, pooling hides
   them).
2. **Non-T configs on QA are closed-book.** T bundles docstore *access*
   (CCI's "tool definitions" semantics), so the T effect = access +
   interface. The alternative (inline paragraphs for parity) isolates pure
   interface at the cost of a large prompt-length asymmetry. Revisit only as
   an explicit new arm.
3. **No LLM judge anywhere in Y.** Judge error is differential in treatment
   (verbose SR/R styles sway judges) — structurally poisonous for component
   effects. Deterministic program graders only; the sympy string-fallback
   path is logged per row for sensitivity checks.
4. **Universal decoupled submission.** Every config, including Bare, can
   submit via `Answer:`; CCI's submission-inside-T is reproduced only in the
   bridge arm. Otherwise T would mechanically dominate through the grading
   interface, not through problem solving.
5. **One strict textual tool grammar, no native function calling.** Native
   tool APIs differ by family and would confound model family with
   interface. Single retry on parse failure, event-logged; grammar failures
   are themselves outcomes (P(answered), finish_reason).
6. **api_error is infrastructure, not an outcome.** Terminal client failures
   are logged to `failures.jsonl`, never persisted as completed rollouts,
   and re-run on resume (decided after smoke 1025599, where 404s were stored
   as done and blocked resume).
7. **Full node always; `one_gpu` means footprint, not allocation.** Small
   models run as 4 independent replicas per node (throughput), big models as
   one TP=4 server. One model per node; parallelism happens across nodes.
8. **Multi-benchmark jobs reuse warm servers.** `BENCH=a,b,c` runs bands
   sequentially in one job (one model load instead of four). Per-bench jobs
   remain valid for maximum node-parallelism.
9. **Committed seeded task lists; compute nodes are hermetic.** N=100 per
   (benchmark, band), seed 20260723, IDs + normalized data + provenance meta
   in git; builders run on login nodes/locally only.
10. **Model revisions pin to a lock file**, not into `models.yaml` —
    preserves the registry's rationale comments; `load_registry()` merges.
11. **Registry substitutions are recorded, never silent** (spec §6): GLM-5.x
    (753B) → Tier S with the Claw-anchor loss stated; Seed-2.0-mini absent →
    parked substitute; Mistral/Qwen slots resolved to what actually exists,
    with cross-vintage caveats where pairs span generations.
12. **`meta` as a sixth column role.** Provenance/bookkeeping columns
    (rollout_key, manifest_ref, seed, node…) are neither covariates nor
    outcomes; the loader rejects them as covariates like post-treatment.
13. **Confidence fallback is `None` + flag, not a fabricated number.**
    Calibration metrics use elicited-confidence rows only;
    `confidence_source` marks the rest.
14. **Wall-clock is diagnostic; cost = tokens, characters, GPU-seconds.**
    Characters are the tokenizer-invariant unit required for cross-family
    comparisons; vLLM prefix caching stays ON (legitimate incremental
    decoding), cache stats are billing diagnostics, never capability.
15. **The harmony tokenizer vocab is vendored in git, sha256-pinned.**
    openai_harmony (vLLM's gpt-oss chat renderer) downloads
    `o200k_base.tiktoken` on first request; the download is impossible on
    compute nodes and fails on JUPITER login nodes too. A 3.6 MB asset whose
    hash harmony itself pins (`446a9538…`) is committed at
    `assets/harmony-vocab/` and served via `TIKTOKEN_ENCODINGS_BASE` — the
    hermetic-benchmarks rule (§4.2.3) extended to tokenizer assets: nothing
    a rollout needs may depend on the network.
16. **Probe before pilot, per family.** One raw-response probe job
    (`slurm/probe.sbatch`) runs the instrument's exact BARE and T prompts
    against a freshly served model and dumps the complete message
    (content/reasoning/tool_calls/stop reasons) BEFORE any pilot rollouts.
    Adopted after gpt-oss-20b: 90 % no_answer on hotpotqa traced to (a) all
    tokens flowing into the hidden harmony reasoning channel with
    `content=null` (`finish_reason=length` even at 1024), and (b) tool
    prompts triggering NATIVE harmony tool calls (`stop_reason=200012`,
    `<|call|>`) instead of textual `Action:` lines — a family×interface
    incompatibility no local test could catch. The probe is the onboarding
    step that separates "model can't do the task" from "interface can't
    carry the model" before the difficulty gate consumes either.
17. **gpt-oss dropped from the MVP factorial: component T is undeliverable.**
    Probes 1033971/1034289: any prompt mentioning tools makes gpt-oss emit a
    native harmony tool call (`<|call|>`, stop_reason 200012) instead of the
    textual `Action:` line — at 92/1024 tokens, unconverted by the loop's
    retry nudge. A model that cannot receive the T treatment cannot occupy
    the 16 of 32 cells containing T. BARE was rescuable
    (reasoning_effort=low + ~2048 budget → clean `Answer:` line), so this is
    interface, not capability — recorded as a family×interface finding for
    the DATASHEET, with the 20b pilot slices kept as evidence. Suppressing
    token 200012 via logit_bias was considered and rejected: it edits the
    sampling distribution in a treatment-correlated way. Revisit post-MVP as
    an explicit native-interface arm.
18. **Phase-4 difficulty-gate rulings** (pilot jobs 1034331/1034587, N=20
    tasks x 2 seeds, window [0.15, 0.85] on BARE/T accuracy):
    mistral x {hotpotqa .204/.183, musique .460/.469, math .400/.300} and
    qwen x {musique .436/.397, gsm8k .725/.575, math .325/.225} enter the
    full 32-config grid. mistral x gsm8k: BARE .875 saturates -> retained
    only as the 4-config thin arm (§4.4's saturation-adjudication
    provision). qwen x hotpotqa: BARE .144 is within sampling noise of the
    floor (SE≈.055 at n=40) with T=.385 mid-window -> admitted, flagged.
    Recorded anomaly for the DATASHEET: musique (hard) outscores hotpotqa
    (easy) on BOTH models' BARE — alias-max F1 generosity and/or
    contamination; the bands are labels, not a verified difficulty
    ordering. Throughput constant set to 4000 rollouts/node-hour — the
    conservative floor of measured steady-state (4.3k mistral-math to 20k
    qwen-easy) — so budget over-estimates.
19. **Deep eval by superset extension, not resampling.** Task lists grow
    only by APPENDING a seeded sample of unused pool entries
    (`build_tasks.py --extend`; the prefix is asserted byte-identical), so
    every completed rollout keeps resuming and deep-eval jobs pay only the
    increment. Targets: QA bands to 500 sampled tasks (SEs shrink ~2.2x);
    gsm8k and MATH L4-5 to CENSUS (all 1319 / all 262 pool tasks — task-
    sampling uncertainty within those benchmarks becomes finite-population
    zero). Manifests now hash the task-list content (`tasks_sha256`) so
    every run pins which population it saw. Estimand scope unchanged:
    fixed factors, conditional on the committed lists.
20. **Census slices ship as sharded parquet chains.** Full-benchmark
    coverage (hotpotqa 7405, musique 2417, gsm8k 1319, math 262) makes a
    slice ~1.18M rollouts: (a) one store has one writer, so a census slice
    runs as a Slurm dependency CHAIN (afterany) of walltime windows, each
    resuming the store — `submit_census.sh`; (b) its panel exceeds git
    limits as one file, so aggregate shards into `panel_partNN.parquet`
    (~300k rows, zstd) and every reader globs `panel*.parquet`; the size
    guard exempts results parquet from the 20 MB pool but caps files at
    95 MB (GitHub hard limit). Budget: ~3.65M rollouts, ~250-300
    node-hours, 8 parallel chains, wall-clock ~3-5 days.
21. **Pin the torch stack; guard the serve path, not just `import vllm`.**
    A stray `uv pip install` re-resolved deps and bumped torch 2.11.0 ->
    2.13.0+cu130 under the wheel-installed vLLM 0.25.1 (no `vendor/vllm`
    source tree exists — the wheel path won at setup). vLLM's compiled C
    extensions (torchvision ops, `_vllm_fa2_C`/`_fa3_C`, `vllm._C`) are
    ABI-linked to torch 2.11.0, so every `vllm serve` crashed —
    `torchvision::nms does not exist`, then after removing torchvision,
    `requires the CUDA flash attention extensions`. It killed the entire
    census + arms fleet: each node hung to the 40-min health ceiling
    (exit 4) producing zero rollouts, while a bare `import vllm` still
    passed (flash-attn loads lazily at serve, not import) — so a naive
    resubmit-gate green-lit doomed jobs. Decisions: (a) `setup_env.sh`
    pins the matched set `vllm==0.25.1` + `torch==2.11.0` +
    `torchvision==0.26.0` + `torchaudio==2.11.0`, the torch trio installed
    LAST with `--no-deps` so no later resolve can drift it; (b)
    `serve_node.sh` runs a ~5 s preflight that imports a flash-attn C
    extension and exits 6 with the fix BEFORE spawning servers, instead of
    burning 40 min per node; (c) recovery is a `--no-deps --force-reinstall`
    of the torch trio — no rebuild, since torch stayed CUDA-enabled and it
    was a pure version skew. Fix confirmed: census resumed 1,110,391 ->
    1,118,301 within minutes. Never `uv pip install -U` in this venv
    without `--no-deps` or a torch constraint.
22. **Duplicate units of work exist in the pre-padding stores; `verify`
    cannot see them.** Adding `padded_components` to the cell identity
    (§4.3.3, so padded-P would not collide with real P) changed every
    `rollout_key`, so each slice that had already run under the old schema
    re-ran its wave-1 tasks once: exactly 16,000 rows (32 configs x 100
    tasks x 5 seeds) on top of gsm8k and math, and the same volume mixed
    into the QA scatter. The rows are real rollouts with unique keys — key
    uniqueness is what `verify` checks, so it passes — but they duplicate
    `(cell, task, seed)`, giving those 100 tasks k=10 where the rest have
    k=5. Decisions: (a) `aggregate` always reports the duplicate count and
    drops them only under `--dedupe`, since silently changing already-
    shipped panels is worse than a loud number; (b) progress is measured on
    unique `(cell, task, seed)`, never on line counts; (c) a future cell-
    identity change is a breaking change — bump the store directory, do not
    re-key in place.
23. **Gate rulings and slice targets are machine-readable, not prose.**
    Which (model, band) slices belong in the census lived only in comments
    across `mvp_grid.yaml`, `submit_census*.sh` and ADR 18, so "what is
    still missing" could not be answered mechanically — wave 2 sat
    unsubmitted for a day behind a green-looking dashboard. `configs/
    gates.yaml` now holds the rulings (`census|thin|dropped|bridge_only|
    pending_gate|unprobed|blocked` + the pilot BARE/T numbers), and
    `harnesslab progress` computes each slice's target from its OWN spec
    (configs x in-scope tasks x seeds) and lists gated slices with no store
    or an unfinished one. This kills the two dashboard lies: a complete
    4-config thin arm reading 13% against the 32-config denominator, and a
    capped slice reading 147% because pre-cap orphans inflate the count.
    `gate_report.sh <model>` reads a finished pilot and prints the ruling
    in ADR 18's order (BARE saturation first, then either-arm-in-window,
    then floor) so onboarding a model is mechanical.
24. **huggingface_hub belongs to the pinned set; the preflight walks the CLI
    entry point.** 2026-07-27, mid-census: new `vllm serve` processes started
    dying with `ModuleNotFoundError: No module named
    'huggingface_hub.utils._terminal'` while already-running servers kept
    answering 200 OK — five jobs lost in ~2 min each (exit 1), six more to
    the 40-min ceiling. The traceback runs `.venv/bin/vllm` ->
    `vllm.entrypoints.cli.main` -> `vllm.config` -> `transformers` ->
    `huggingface_hub.utils.__init__` -> `_cache_manager` -> `from ._terminal
    import tabulate`. Two findings: (a) `pyproject` bounds the hub only at
    `>=0.30`, so any resolve can move it under a running fleet — it is part of
    the matched instrument set exactly like torch, and `setup_env.sh` now pins
    it (`HF_HUB_PIN`); (b) the ADR 21 preflight imported `vllm` plus a
    flash-attn extension, which never touches transformers, so it would have
    green-lit every one of these jobs. The preflight now imports the CLI entry
    point itself and reports the real exception, routing to the hub fix or the
    torch fix by matching the message. `scripts/hpc/check_env.sh` is the same
    check as a standalone command — run it after ANY venv change and before
    queued jobs start into it. Operational rule, now twice-learned: never
    `pip install` while jobs are starting. pip unlinks before it relinks, so a
    job importing during that window dies on a half-written package while the
    identical import succeeds a second later on the login node — which is why
    the login-node check passed while the fleet failed. Chains are
    resume-safe, so the recovery is to fix the venv and let the pending links
    heal themselves; resubmitting instead would put two writers on one store.
25. **Health ceiling raised to 90 min; it was sized for a quarter of the
    fleet.** The 40-min wait in `serve_node.sh` dates from ~4 concurrent jobs.
    At 20-30 jobs all streaming weights off the same `$SCRATCH` GPFS cache,
    cold loads of the 26B+ models miss it: on 2026-07-27 four chains burned
    TWO links each back to back (gemma-e4b hotpotqa, scout gsm8k, kimi gsm8k,
    qwen-122b musique) while the same models came up fine on less contended
    nodes — 58 FAILED in 24 h, nearly all exit 4, and the affected slices show
    NO STORE because no link ever reached the rollout loop. The asymmetry
    decides it: a link that waits longer costs minutes off an 11.5 h window; a
    link that dies costs 40 min AND a chain slot, and a chain that runs out
    leaves a slice stalled indefinitely. `HEALTH_WAIT_S` (default 5400)
    overrides it per submission, and the failure path now prints the last 5
    lines of the server log so exit 4 says WHY instead of just "FAILED".
26. **Resume is planned from the remaining work, not from a guessed chain
    length.** Chains are submitted at a fixed number of links; links die at
    the health ceiling or exit at the 11.5 h walltime, and when the last one
    goes the slice simply stops producing — silently, because a store that is
    not being written looks exactly like one that is between links. On
    2026-07-27/28 all 18 in-flight slices drained within a few hours of each
    other and the fleet sat idle. `harnesslab plan` emits, per unfinished
    gated slice, the rollouts still owed and a chain length sized from them
    (`--per-link`, default 40,000 — under one link at mvp_grid's conservative
    4000/node-hour floor); `scripts/hpc/resume_all.sh` consumes it and
    submits. Two properties make it safe to re-run unattended: a slice with a
    link already queued is SKIPPED, so the single-writer rule cannot be
    violated, and an over-long chain costs nothing because a surplus link
    finds no pending rollouts and exits in minutes. Under-provisioning is the
    only expensive error, so `plan` rounds up.
