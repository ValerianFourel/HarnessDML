# halcausal

Causal re-analysis of the Holistic Agent Leaderboard (HAL) rollouts
([arXiv:2510.11977](https://arxiv.org/abs/2510.11977)) using Double Machine
Learning. Mission, phases, and guardrails: [CLAUDE.md](CLAUDE.md).

## Architecture

Three environments, GitHub is the bus, one `main` branch, **path discipline
instead of branches**:

| environment | runs | commits |
|---|---|---|
| LOCAL (Claude Code) | code writing, review, Phase-5 analysis from `results/` | `src/`, `notebooks/`, `configs/`, `scripts/`, `schema/column_roles.yaml`, `reports/` |
| HPC (JupyterHub) | download+decrypt to scratch, ETL, estimation | `results/` and `schema/` **only** (enforced by `scripts/check_results_size.py`) |
| GitHub | — | — |

Both sides `git pull --rebase` before every push. Raw data never enters git:
`data` is a gitignored symlink to `$HAL_DATA_DIR` on scratch, and the size
guard hard-fails any staged file > 25 MB or outside `results/` + `schema/`.

Notebooks are thin orchestration (import package → call → display). All logic
lives in `src/halcausal/` so every substantive line is reviewable in a diff.

## Status

- [x] Phase 0 — skeleton: package, guards, configs, notebook stubs (LOCAL)
- [ ] Phase 1 — download one slice, decrypt, empirical `schema/SCHEMA.md` (HPC)
- [ ] Phase 2 — ETL → `results/panel/<benchmark>.parquet` (HPC)
- [ ] Phase 3 — design diagnostics + `design_notes.md` gate (HPC)
- [ ] Phase 4 — DML estimation + comparison ladder + sensitivity (HPC)
- [ ] Phase 5 — analysis from `results/` (LOCAL)

## Local setup

```sh
uv sync            # venv + editable install of halcausal
uv run pytest      # guards must be green before any push HPC consumes
```

## HPC bootstrap (JupyterHub / login node — internet required)

Run once, top to bottom, from a login or JupyterHub terminal node. Compute
nodes are assumed offline; everything network-touching happens here or in
`notebooks/01_download_decrypt.ipynb`.

```sh
# ── 1. Python ≥ 3.11 ────────────────────────────────────────────────────────
module load python/3.12 2>/dev/null || module load python 2>/dev/null || true
python3 --version   # need ≥ 3.11. If the module system has none:
# micromamba fallback (user-space, no admin):
#   curl -Ls micro.mamba.pm/install.sh | bash
#   micromamba create -n halcausal -c conda-forge python=3.12
#   micromamba activate halcausal

# ── 2. Clone and enter ──────────────────────────────────────────────────────
git clone <REPO_URL> halcausal && cd halcausal

# ── 3. Scratch layout + env vars ────────────────────────────────────────────
export HAL_DATA_DIR="/scratch/$USER/hal_data"      # adjust to your cluster
mkdir -p "$HAL_DATA_DIR"
ln -sfn "$HAL_DATA_DIR" data                       # gitignored symlink
cp .env.template .env                              # fill in HF_TOKEN etc.

# ── 4. Project venv (plain venv+pip; use uv instead if available) ───────────
python3 -m venv .venv && source .venv/bin/activate
pip install -U pip
pip install -e ".[hpc]"                            # halcausal + papermill/ipykernel
python -m ipykernel install --user --name halcausal --display-name "halcausal"

# ── 5. hal-harness → hal-decrypt (own venv; NOT pip install -e . with deps) ─
# The full hal-harness dependency set pulls agent frameworks (incl. a git
# smolagents pin) we never run. hal-decrypt only imports click, python-dotenv,
# cryptography, rich — verified. Install exactly that:
git clone --depth 1 https://github.com/princeton-pli/hal-harness vendor/hal-harness
python3 -m venv vendor/.hal-venv
vendor/.hal-venv/bin/pip install click python-dotenv cryptography rich
vendor/.hal-venv/bin/pip install --no-deps -e vendor/hal-harness
vendor/.hal-venv/bin/hal-decrypt --help            # must print usage

# ── 6. Auth ─────────────────────────────────────────────────────────────────
# Hugging Face: dataset is public+ungated (verified 2026-07-23); a token still
# avoids anonymous rate limits:
export HF_TOKEN=hf_...                             # or huggingface-cli login
# GitHub: fine-grained PAT (contents: read/write, THIS repo only) or a deploy
# key with write access. Store via:
git config credential.helper store                 # PAT goes to ~/.git-credentials
# or: ssh key in ~/.ssh + remote set to git@github.com:...

# ── 7. Smoke test ───────────────────────────────────────────────────────────
python -c "import halcausal, doubleml, lightgbm, polars; print('halcausal OK')"
```

Then open `notebooks/00_hpc_setup.ipynb` (kernel: `halcausal`) and Run All —
it re-checks all of the above and fails loudly on anything missing.

## Workflow loop

1. LOCAL: write code → `pytest` green → commit code paths → push.
2. HPC: `git pull --rebase` → open next notebook → Run All → `05_export_results`
   writes `results/manifests/<run_id>.json`, runs the size guard, commits
   `results/` (+ `schema/` in Phase 1), pushes.
3. LOCAL: "pull and analyze `<run_id>`" → analysis strictly from `results/`
   and the manifest; findings to `reports/`.

## Data recon (verified locally, 2026-07-23)

- `agent-evals/hal_traces`: public, ungated, flat repo, **380 zips, 113.1 GB**;
  per-benchmark inventory in [reports/hf_inventory.md](reports/hf_inventory.md)
  (regenerate: `python -m halcausal.io.hf`).
- First slice: **`taubench_airline` — 47 files, 3.41 GB** (smallest useful slice;
  `swebench_verified_mini` is 17.8 GB). Under the 5 GB ask-before-download bar.
- Encryption: each zip holds `*.encrypted` JSON (`{"encrypted_data", "salt"}`),
  Fernet + PBKDF2-HMAC-SHA256 (480k iters), fixed password — contamination
  deterrence, not access control. `hal-decrypt` writes decrypted files next to
  the input zips.
- Naming quirks (recorded, resolved from in-trace config during ETL, filenames
  are never trusted): Online Mind2Web runs have **no benchmark prefix** — they
  are the `browser-use_*` and `seeact_*` files; the repo also contains
  **CoLBench** runs, which are not among the paper's 9 benchmarks.
