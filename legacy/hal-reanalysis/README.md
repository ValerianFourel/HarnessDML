# legacy/hal-reanalysis — the observational arm (preserved, paused)

**This is the observational arm** of the research program: causal re-analysis of
HAL agent traces (arXiv:2510.11977) via Double Machine Learning — **Estimand
#1: reasoning effort** — plus the planned Terminal-Bench fusion. **It will be
revived in the data-fusion phase after the factorial MVP. Do not delete.**

State at freeze (2026-07-23, tag `pre-harnesslab`, branch `legacy-hal`):

- Phase 1 complete: `taubench_airline` slice explored on JUPITER (47 runs × 50
  shared tasks = 2,350 rollouts); empirical schema in `schema/SCHEMA.md`;
  exploration read-out in `reports/explore_taubench_airline.md`; 8 logged
  reconciliation items in `reports/discrepancies.md`.
- `schema/field_mapping.yaml` (curated, draft) was awaiting sign-off before
  Phase-2 ETL (`build_panel()` never written).
- Naive headline worth remembering: reasoning effort *hurts* on the HAL
  generalist scaffold but *helps* on TAU-bench-native scaffolds — a
  scaffold×reasoning interaction, and exactly the kind of claim the factorial
  platform (HarnessLab) is being built to identify properly.

Self-contained: `cd legacy/hal-reanalysis && uv sync && uv run pytest`
(26 tests). Decrypted traces live on JUPITER at
`/e/project1/scifi/fourel1/HarnessDML/Data/` (project storage), reached via a
gitignored `data` symlink; the cluster-specific bootstrap is in
`README-halcausal.md` § "This cluster".

Concepts carried forward into HarnessLab (reimplemented there, not imported):
`schema/column_roles.yaml` role registry with a post-treatment covariate hard
error; results-contract size guard (`scripts/check_results_size.py`); run
manifests; `.gitignore` data discipline; JUPITER AArch64 + uv-provisioned
CPython environment notes.
