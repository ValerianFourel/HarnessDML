"""Raw-response probe: what does a gpt-oss vLLM server actually return for
the instrument's exact prompts?

Motivated by pilot slice pilot_gpt_oss_20b_hotpotqa: 90% no_answer, ZERO
textual tool calls across 120 T-config rollouts, near-empty `content`, and
tokens_out ~240-470 — the model works in the hidden harmony channel and
often never emits a visible final message. This dumps the COMPLETE response
message (content, reasoning, tool_calls, finish/stop reasons) for BARE and
T prompts under a few request variants, so the fix is chosen from evidence.

Runs inside slurm/probe.sbatch (servers up, BASE_URLS set). Diagnostic
only: no stores, no results/ artifacts; output stays in the job log.
"""

from __future__ import annotations

import json
import os
import sys

import httpx

from harnesslab.components import compose
from harnesslab.experiment import load_registry
from harnesslab.tasks import load_tasks

VARIANTS = [
    ("default", {}),
    ("max1024", {"max_tokens": 1024}),
    ("effort_low", {"reasoning_effort": "low"}),
    ("no_reasoning", {"include_reasoning": False}),
]


def clip(x, n=400):
    if isinstance(x, str):
        return x if len(x) <= n else x[:n] + f"...[+{len(x) - n} chars]"
    if isinstance(x, list):
        return [clip(v, n) for v in x]
    if isinstance(x, dict):
        return {k: clip(v, n) for k, v in x.items()}
    return x


def main() -> int:
    base = os.environ["BASE_URLS"].split(",")[0].rstrip("/")
    model_id = sys.argv[1] if len(sys.argv) > 1 else "gpt_oss_20b"
    served = load_registry()[model_id]["hf_id"]
    task = load_tasks("configs/tasks/hotpotqa.jsonl")[0]
    prompts = {
        "BARE": compose("qa", frozenset()).text,
        "T": compose("qa", frozenset({"T"})).text,
    }
    print(f"[probe] {model_id} -> {served} via {base}; task {task['task_id']}")
    with httpx.Client(base_url=base, timeout=300.0) as http:
        for cfg, sys_text in prompts.items():
            for vname, extra in VARIANTS:
                payload = {
                    "model": served,
                    "messages": [
                        {"role": "system", "content": sys_text},
                        {"role": "user", "content": task["question"]},
                    ],
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "seed": 0,
                    "max_tokens": 256,
                    **extra,
                }
                r = http.post("/chat/completions", json=payload)
                print(f"\n===== {cfg} / {vname} -> HTTP {r.status_code}")
                try:
                    data = r.json()
                except Exception:  # noqa: BLE001
                    print(clip(r.text, 600))
                    continue
                if r.status_code != 200:
                    print(json.dumps(clip(data), indent=1))
                    continue
                choice = data["choices"][0]
                msg = choice["message"]
                print(
                    "finish_reason:", choice.get("finish_reason"),
                    "| stop_reason:", choice.get("stop_reason"),
                    "| usage:", data.get("usage"),
                )
                print("message keys:", sorted(msg.keys()))
                print(json.dumps(clip(msg), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
