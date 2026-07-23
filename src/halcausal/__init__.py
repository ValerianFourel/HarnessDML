"""Causal re-analysis of HAL agent rollouts (arXiv:2510.11977) via DML.

Split local/HPC workflow — see CLAUDE.md. Notebooks stay thin; all logic
lives here. Keep this __init__ import-light so offline compute nodes can
`import halcausal` without touching network-facing libraries.
"""

__version__ = "0.1.0"

from . import guards, paths  # noqa: F401
