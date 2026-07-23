# Overview — what HarnessLab is trying to achieve

## The problem

Agent benchmarks compare *bundled* harnesses: a leaderboard entry is a model
⊗ prompt scaffold ⊗ tool interface ⊗ budget ⊗ evaluator, and any of those can
be responsible for a gap. Three research legs each solved one piece and
stopped:

- **CCI** (arXiv:2605.05716) ran a true 2⁵ factorial over five scaffold
  components and found **sign-flipping interactions** (a component that helps
  one model hurts another) — but on toy tasks, with attribution only, no
  inference.
- **Claw-SWE-Bench** (arXiv:2606.12344) showed how to make differences
  *attributable*: fix everything except the treatment (prompt, budget,
  container, evaluator). But it varied whole bundled harnesses, single runs,
  no uncertainty.
- **Towards a Science of AI Agent Reliability** (arXiv:2602.16666) argued
  outcomes are **distributions over repeated runs** — consistency,
  calibration, robustness — not scalar accuracy. But the scaffold never
  varied, so nothing causal about harness design.

HarnessLab combines all three legs: CCI's factorial over components ×
Claw's everything-else-fixed attribution discipline × reliability-style
K-seed distributional outcomes — on real benchmarks, self-hosted open-weight
models, with actual statistical inference.

## What no one else has (the unclaimed territory)

Conditional component effects τ_s(C, Z) with interaction structure and
**simultaneous inference**; repeated-seed distributional outcomes; mediation
via trace features; constrained configuration policy with LOFO validation;
fully reproducible self-hosted open weights. Adjacent work and why it
doesn't cover this (full register goes verbatim into DATASHEET.md):
Harness-Bench (bundled configs, single runs, LLM-judged, disclaims causal
decomposition); Agent Arena (IPW *marginal* effects vs a uniform baseline —
exactly the estimand CCI's sign-flips break; K=1); AHE (harness evolution
with OFAT ablations that observe but cannot identify interactions);
2606.09774 (Resolution-IV fractional factorial, single domain).

**This platform's product is the dataset that makes the analysis
identifiable.** Estimation (DoubleML, CATE learners) is a downstream
consumer; this repo builds the data contract, not the estimators.

## The design in one screen

- **Treatments**: five binary components, faithfully reconstructed from CCI
  then frozen (content-hashed into every manifest) — P Planning, T Tool Use,
  M Memory, SR Structured Reasoning, R Reflection → 2⁵ = 32 configurations.
  Secondary arms (not fully crossed): 3 component orderings, 3 paraphrase
  template variants.
- **Everything else fixed**: one ReAct-style loop, one strict textual action
  grammar (`Search[q]`, `Lookup[k]`, `Calculate[e]` — no native function
  calling, which would confound model family with interface), one universal
  `Answer:` submission line in *every* config (deviation from CCI, with a
  bridge arm reproducing their T-coupled submission for reconciliation).
- **Benchmarks** (hermetic, offline, committed 100-task seeded lists): QA
  easy/hard = HotpotQA-distractor / MuSiQue; math easy/hard = GSM8K /
  MATH levels 4–5. A **difficulty gate** keeps each (model, band) only where
  Bare/T accuracy lands in [0.15, 0.85] — no ceiling/floor cells.
- **Outcomes**: Y (F1/EM, unanswered ⇒ 0) with a mandatory decomposition
  (P(answered) = grader-interface channel; success|answered flagged as
  descriptive); cost in tokens/characters/GPU-seconds; and cell-level
  distributional metrics over K=5 seeds (outcome consistency C_out,
  trajectory consistency via JSD and Levenshtein, resource consistency,
  pass@k / pass∧k, ECE / AUROC / Brier from elicited confidence).
- **Grading is deterministic programs only — no LLM judge anywhere in Y.**
  A judge's error would be *differential in treatment* (verbose SR/R styles
  sway judges), which is poison for component effects.
- **Confounding controls are engineered, not assumed**: seeded random
  interleaving of (config, task, seed) within every job (no config runs in a
  contiguous block); length-matched padding pseudo-components (content vs
  prompt-length); per-rollout node/timestamps/server-uptime logging;
  per-request sampling seeds.
- **Models**: tiered registry of open weights served with vLLM on JUPITER
  GH200 nodes — frontier Tier F (DeepSeek-V4-Flash, Qwen3.6-27B,
  Llama-4-Scout, Mistral-Small-3.2, gpt-oss-120b, Gemma-4-26B-A4B), weak-pole
  Tier G (gpt-oss-20b, Qwen3.5-9B, Ministral-3-3B, Gemma-4-E4B), bridge
  Tier B (Llama-3.1-8B, CCI's validated cell). Within-generation F/G pairs
  give capability moderation without confounding post-training vintage.

## What we will and will not claim

Estimands are defined in [ESTIMANDS.md](../ESTIMANDS.md): per-component
effects under the uniform-factorial measure, the full interaction
decomposition with a sign-flip register under simultaneous coverage, cell
means with an anti-winner's-curse best-arm protocol, cost frontiers, and
reliability functionals. Models, families, bands, templates are **fixed
factors** — inference is conditional on the tested grid; the only
generalization statements are empirical leave-one-family-out and
leave-one-band-out splits. Cross-family comparisons are observational bundle
comparisons and are labeled as such, always.
