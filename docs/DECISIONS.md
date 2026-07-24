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
