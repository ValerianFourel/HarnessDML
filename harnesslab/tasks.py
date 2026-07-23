"""Committed-task loading (§4.4). Tasks ship as jsonl, one object per task.

Required: task_id, question. QA additionally: paragraphs (list of [title,
text] — the hermetic docstore corpus) and answers (gold + aliases). Math
additionally: gold (GSM8K number string or MATH latex-ish answer).
"""

from __future__ import annotations

import json
from pathlib import Path


def load_tasks(path: Path | str) -> list[dict]:
    tasks: list[dict] = []
    seen: set[str] = set()
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            task = json.loads(line)
            for key in ("task_id", "question"):
                if key not in task:
                    raise ValueError(f"{path}:{i + 1}: missing {key!r}")
            if task["task_id"] in seen:
                raise ValueError(f"{path}:{i + 1}: duplicate task_id {task['task_id']!r}")
            seen.add(task["task_id"])
            tasks.append(task)
    if not tasks:
        raise ValueError(f"{path}: no tasks")
    return tasks
