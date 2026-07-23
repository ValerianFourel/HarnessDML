# results/ — the only artifacts HPC commits

Contract (enforced by `scripts/check_results_size.py`; full text in CLAUDE.md):
small, final, self-describing files only — never anything from `data/`.

- `panel/<benchmark>.parquet` — flat analysis panel (one row per rollout)
- `diagnostics/` — overlap/cell-count tables, propensity summaries,
  estimable-contrast list (json), `design_notes.md` (the Phase-4 gate)
- `estimates/<estimand_id>/` — estimates + cluster-robust CIs, comparison
  ladder (naive / clustered-OLS / DML), GATE tables, bootstrap draws,
  sensitivity output
- `figures/` — png, colorblind-safe, matplotlib
- `manifests/<run_id>.json` — mandatory provenance per run; every artifact
  filename embeds its `run_id`

Hard limits: paths outside `results/` + `schema/` unpushable; no file > 25 MB.
