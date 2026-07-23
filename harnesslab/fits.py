"""fits-check (§6): params × dtype vs GH200 memory → serving_mode.

Heuristic: BF16 weights (2 bytes/param) × 1.35 overhead (KV cache, activations,
CUDA context) against 90% of 96 GB (one GPU) / 384 GB (one node, TP=4).
Entries with unknown params (verify pending) are reported, not judged.
"""

from __future__ import annotations

GPU_GB = 96.0
NODE_GPUS = 4
OVERHEAD = 1.35
BYTES_PER_PARAM = {"bf16": 2.0, "fp8": 1.0}  # fp8: DeepSeek-style native weights
USABLE = 0.9


def required_gb(params_b_total: float, dtype: str = "bf16") -> float:
    return params_b_total * BYTES_PER_PARAM[dtype] * OVERHEAD


def serving_mode_for(params_b_total: float, dtype: str = "bf16") -> str:
    need = required_gb(params_b_total, dtype)
    if need <= GPU_GB * USABLE:
        return "one_gpu"
    if need <= GPU_GB * NODE_GPUS * USABLE:
        return "one_node_tp4"
    return "multi_node"


def check_registry(registry: dict[str, dict]) -> list[dict]:
    """One row per model: declared vs computed serving_mode."""
    rows = []
    for model_id, entry in registry.items():
        params = entry.get("params_b_total")
        dtype = entry.get("dtype", "bf16")
        computed = serving_mode_for(float(params), dtype) if params else None
        rows.append({
            "model_id": model_id,
            "tier": entry["tier"],
            "params_b_total": params,
            "declared": entry["serving_mode"],
            "computed": computed or "UNKNOWN (verify)",
            "ok": (computed is None) or (computed == entry["serving_mode"]),
        })
    return rows
