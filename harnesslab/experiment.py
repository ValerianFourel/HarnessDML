"""Experiment specification (configs/experiments/*.yaml) and model registry.

One spec = one (model, benchmark) slice of a grid; Slurm arrays iterate specs
with CLI overrides (§7). Bands, caps, and family derive from the benchmark.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from . import benchmarks
from .components import ORDERINGS, TEMPLATE_IDS, config_id

_REGISTRY_PATH = Path(__file__).resolve().parents[1] / "configs" / "models.yaml"


def load_registry(path: Path | str | None = None) -> dict[str, dict]:
    p = Path(path) if path else _REGISTRY_PATH
    models = yaml.safe_load(p.read_text())["models"]
    # revisions pinned by prefetch land in a lock file (keeps models.yaml
    # comments intact — the "write back SHAs" of §6/§7)
    lock = p.parent / "model_revisions.lock.yaml"
    if lock.exists():
        for model_id, revision in (yaml.safe_load(lock.read_text()) or {}).items():
            if model_id in models:
                models[model_id]["revision"] = revision
    return models


@dataclass(frozen=True)
class CellConfig:
    components: frozenset[str]
    ordering_id: str = "o1"
    template_id: str = "t1"
    padding_components: frozenset[str] = frozenset()

    @property
    def config_id(self) -> str:
        return config_id(self.components)


@dataclass
class ExperimentSpec:
    exp_id: str
    benchmark: str
    model_id: str
    configs: list[CellConfig]
    k_seeds: int
    temp: float = 0.1
    top_p: float = 0.9
    schedule_seed: int = 0
    tasks_file: str = ""
    n_tasks: int | None = None  # first N of the committed list (pilot slices)
    concurrency: int = 4
    system_role_mode: str = "native"
    elicit_confidence: bool = True
    coupled_submission: bool = False  # bridge arm only (§4.2.1)
    model_family: str = ""
    model_scale_b: float = 0.0
    model_hf_id: str = ""      # manifest provenance (§1.4: hf repo + revision)
    model_revision: str = ""
    throughput_rollouts_per_node_hour: float | None = None  # set from pilot (§7)
    extra: dict = field(default_factory=dict)

    @property
    def family(self) -> str:
        return benchmarks.family(self.benchmark)

    @property
    def band(self) -> str:
        return benchmarks.band(self.benchmark)

    @property
    def step_cap(self) -> int:
        return benchmarks.STEP_CAP[self.band]

    @property
    def max_new_tokens_step(self) -> int:
        return benchmarks.MAX_NEW_TOKENS_STEP[self.band]

    @property
    def timeout_s(self) -> float:
        return benchmarks.WALL_TIMEOUT_S[self.band]

    @property
    def seeds(self) -> list[int]:
        return list(range(self.k_seeds))

    def cell_dict(self, cfg: CellConfig) -> dict:
        """The cell identity used for rollout keys and panel rows."""
        return {
            "model_id": self.model_id,
            "benchmark": self.benchmark,
            "band": self.band,
            "config_id": cfg.config_id,
            "ordering_id": cfg.ordering_id,
            "template_id": cfg.template_id,
            "temp": self.temp,
        }


def _validate(spec: ExperimentSpec) -> ExperimentSpec:
    if spec.benchmark not in benchmarks.BENCHMARKS:
        raise ValueError(f"unknown benchmark {spec.benchmark!r}")
    for cfg in spec.configs:
        if cfg.ordering_id not in ORDERINGS or cfg.template_id not in TEMPLATE_IDS:
            raise ValueError(f"bad ordering/template in {cfg}")
    if spec.system_role_mode not in ("native", "prepended"):
        raise ValueError(f"bad system_role_mode {spec.system_role_mode!r}")
    if spec.k_seeds < 1:
        raise ValueError("k_seeds must be >= 1")
    return spec


def served_model_name(spec: ExperimentSpec, registry: dict[str, dict] | None = None) -> str:
    """vLLM serves models under their hf_id; the registry key is ours only.
    (Asking a vLLM server for the registry key 404s — smoke run 1025599.)"""
    if spec.model_id == "mock":
        return "mock"
    reg = registry if registry is not None else load_registry()
    return reg[spec.model_id]["hf_id"]


def resolve_model(spec: ExperimentSpec, registry: dict[str, dict] | None = None) -> None:
    """Fill model_family/model_scale_b from the registry ('mock' is special)."""
    if spec.model_id == "mock":
        spec.model_family = spec.model_family or "mock"
        spec.model_hf_id = spec.model_hf_id or "mock"
        return
    reg = registry if registry is not None else load_registry()
    entry = reg[spec.model_id]
    spec.model_family = entry["family"]
    spec.model_scale_b = float(entry.get("params_b_total") or 0.0)
    spec.model_hf_id = entry["hf_id"]
    spec.model_revision = entry.get("revision") or "main"


def from_yaml(
    path: Path | str,
    registry: dict[str, dict] | None = None,
    overrides: dict | None = None,
) -> ExperimentSpec:
    raw = yaml.safe_load(Path(path).read_text())
    if overrides:
        raw.update(overrides)
    configs = [
        CellConfig(
            components=frozenset(c.get("components", [])),
            ordering_id=c.get("ordering_id", "o1"),
            template_id=c.get("template_id", "t1"),
            padding_components=frozenset(c.get("padding_components", [])),
        )
        for c in raw.pop("configs")
    ]
    known = {f.name for f in ExperimentSpec.__dataclass_fields__.values()}  # type: ignore[attr-defined]
    extra = {k: raw.pop(k) for k in list(raw) if k not in known}
    spec = ExperimentSpec(configs=configs, extra=extra, **raw)
    resolve_model(spec, registry)
    return _validate(spec)
