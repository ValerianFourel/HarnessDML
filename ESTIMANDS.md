# ESTIMANDS.md — what HarnessLab estimates, and what it refuses to claim

Written at Phase 0; governs every REPORT and every analysis consumer. The
platform's job is to make these estimands identifiable **by design**;
estimation (DoubleML etc.) is downstream.

## 1. Units, notation, assignment

- **Component vector** S = (P, T, M, SR, R) ∈ {0,1}⁵; configuration = one of
  32 cells of the full factorial. Secondary treatment coordinates: ordering
  O ∈ {o1,o2,o3}, template V ∈ {t1,t2,t3} (not fully crossed; default o1/t1).
- **Context** Z = (model m, family, scale, benchmark, band) — fixed factors,
  chosen not sampled. Design constants per arm: temperature, top_p, caps.
- **Rollout** r = (cell c, task i, seed k); cell c = (m, b, S, O, V, temp);
  task i ∈ committed lists (`configs/tasks/`, N=100 per benchmark-band);
  seed k = 1..K (K=5 primary, 10 headline, 3 temp-0 arm).
- **Assignment.** S, O, V are assigned deterministically by design over the
  full factorial within every gated (m, b) — every component is independent
  of task and of the other components by construction (balanced orthogonal
  design ⇒ randomization inference is available; execution order within jobs
  is additionally randomized via `schedule.py` to break time/server-state
  confounding). Identification of component effects therefore rests on the
  design, not on unconfoundedness assumptions.
- **Interference caveat.** Rollouts share vLLM servers; co-load could couple
  outcomes (latency, truncation-at-timeout). Mitigations: interleaved
  schedule, per-rollout server-uptime/node logging, wall-clock demoted to
  diagnostic. Residual interference is reported as a limitation, not
  assumed away.
- **Potential outcomes.** Y_r(s) for s ∈ {0,1}⁵ at fixed Z and design
  constants. All estimands below are functionals of {Y_r(s)} within the
  tested grid.

## 2. Primary estimands

**E1 — Per-component conditional effects (uniform-factorial measure).**
For component j and context (m, b):

  τ_j(m, b) = 2⁻⁴ · Σ_{s₋ⱼ ∈ {0,1}⁴} E_i,k [ Y(s₋ⱼ, sⱼ=1) − Y(s₋ⱼ, sⱼ=0) | m, b ]

i.e. the main effect averaged over the *uniform* distribution of the other
four components — equivalently 2·βⱼ in the saturated ±1-coded regression.
This is a **design-measure estimand**: it answers "what does toggling j do,
averaged over the co-component grid", not "averaged over some deployment
policy". (Contrast: Agent Arena's IPW marginal against a uniform baseline
targets the same functional only under no interactions — precisely the
assumption CCI's sign-flips falsify. We report τ_j(m,b) per stratum and never
pool over Z without showing the strata.)

**E2 — Interaction structure.**
Saturated factorial decomposition Y = Σ_{A⊆{1..5}} β_A Π_{j∈A} xⱼ (x ∈ {−1,+1})
per (m, b). Deliverables: all |A| ≤ 2 effects with simultaneous confidence
bands; higher-order terms as a pooled variance share (hierarchy/sparsity
diagnostic); and the **sign-flip register**: pairs (j; Z, Z′) where τ_j has
opposite signs with simultaneous coverage (the CCI replication object,
now with inference).

**E3 — Cell means and best-arm.**
μ_S(m, b) = E_i,k[Y | S, m, b] for all 32 cells, with the best-config
protocol of §6 (naive argmax is forbidden — winner's curse).

**E4 — Cost and the cost-accuracy frontier.**
Same E1–E3 functionals with Y replaced by cost outcomes (tokens_out,
chars_out, GPU-seconds), plus the per-(m,b) frontier over cells
(accuracy vs cost, both with uncertainty). Wall-clock never enters E4.

## 3. Y-decomposition (mandatory in every report)

1. **Y** (primary): score with unanswered ⇒ 0. Causal, unconditional.
2. **P(answered)**: probability the `Answer:` line parsed. Causal,
   unconditional — this channel captures *grader-interface* effects
   (components changing format compliance, not problem-solving).
3. **E[Y | answered]**: descriptive only. Conditioning on a post-treatment
   event defines a principal-stratum quantity we do not identify; reported
   with an explicit flag, never as a headline effect.
`finish_reason` distinguishes no_answer / step_cap / timeout / parse_loop /
api_error from a wrong answer; failure-mode composition is itself an outcome.

## 4. Reliability estimands (distributional, cell-level)

Defined per cell over the task × seed distribution (K seeds nested in tasks):
outcome consistency C_out = mean_i(2p̂_i − 1)²; trajectory consistency C^d
(1 − mean pairwise JSD over action-type distributions) and C^s (1 − mean
normalized Levenshtein over action sequences); resource consistency
C_res = exp(−mean CV) over {tokens_out, wall_s, tool_calls}, both conditional
on success and unconditional; pass@k and pass∧k; calibration ECE (10 bins),
AUROC, Brier from elicited confidence (rows with `confidence_source=fallback`
analyzed separately). Treatment effects on these functionals are cell-level
contrasts (e.g. ΔC_out from toggling R), with task-cluster bootstrap
inference. Note: K is small; functional estimates carry finite-K bias
(p̂_i from 5 draws) — report with K in the estimator name (C_out@5) and never
compare across different K.

## 5. Inference discipline

- **Clustering.** Task i is the sampling unit and the cluster for ALL
  standard errors — every cell reuses the same tasks, and seeds are nested
  repetitions. Nothing is ever reported with i.i.d.-rollout SEs.
- **Randomization inference** (design-justified permutations of component
  labels within (m, b)) is the reference analysis for E1 sharp nulls;
  cluster-robust asymptotics for everything else.
- **Simultaneity.** Every report family gets familywise control:
  multiplier-bootstrap sup-t bands for the 5 × (m,b) component-effect table
  and for E2's |A| ≤ 2 sets; Romano–Wolf stepdown for cross-family tables.
  The sign-flip register only admits pairs surviving simultaneous coverage.
- **Task-FE ladder.** The descriptive ladder (analysis/): naive cell means →
  task-fixed-effects OLS with task-clustered SEs → per-component marginals
  stratified by (family, band). The ladder is descriptive; it feeds, never
  replaces, the estimands above.

## 6. "Best config" protocol (anti-winner's-curse)

Claims of the form "config S* is best (for m, b)" require BOTH:
1. **Multiple comparisons with the best** (Hsu's MCB): simultaneous
   intervals for μ_S − max_{S′≠S} μ_{S′}; report the non-dominated set,
   not an argmax.
2. **Seed-split validation**: select S* on a seed subset, estimate its gap
   on held-out seeds (clean post-selection estimate).
Reports show the selected set + both corrected gaps. A bare argmax over 32
noisy cells is winner's-cursed and is not a permitted sentence.

## 7. Scope: fixed factors, no transport

Model, family, scale, band, template are **fixed factors**. All inference is
conditional on the tested grid. No claims about untested or future models; no
superpopulation-of-models language. The only cross-environment statements
permitted are empirical **LOFO** (leave-one-family-out) and leave-one-band-out
splits (aggregate emits the split indices). Cross-family/scale contrasts are
observational comparisons of bundled packages (capability ⊗ post-training
vintage ⊗ tokenizer ⊗ template delivery ⊗ contamination) — the moderator
caveat of CLAUDE.md §4.3.6 attaches verbatim to every such table.
New-model onboarding is a *procedure* (pilot → gate → 4 headline configs
≈ 2k rollouts → partial pooling as shrinkage), never an inference.

## 8. Secondary-arm estimands

- **Padding control**: contrast real component j vs length-matched padding
  pseudo-component — separates content effects from prompt-length effects;
  one Tier-F model × both bands.
- **Bridge arm** (Tier B, CCI coupling): reconciliation contrast between our
  decoupled-submission protocol and CCI's T-coupled one on Llama-3.1-8B —
  validates the re-implemented instrument before Tier-F conclusions.
- **Ordering / template arms**: τ over O and V on their subsets — prompt-
  robustness of component effects (an effect that reverses across paraphrase
  variants is a template artifact, not a component effect).
- **Temp-0 arm**: sensitivity of E1/E2 signs to sampling temperature.

## 9. What this repo does NOT do (this phase)

No DoubleML estimation, no CATE learners, no mediation estimation — the
platform exports tidy DoubleML-ready frames (rollout panel + roles registry +
split indices) and stops. Post-treatment columns are mediators or cost
outcomes; `load_panel` hard-errors if one is requested as a covariate.
