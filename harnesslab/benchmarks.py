"""Benchmark constants (§4.4): families, bands, caps. All offline."""

FAMILY = {"hotpotqa": "qa", "musique": "qa", "gsm8k": "math", "math": "math"}
BAND = {"hotpotqa": "easy", "musique": "hard", "gsm8k": "easy", "math": "hard"}

STEP_CAP = {"easy": 4, "hard": 6}
MAX_NEW_TOKENS_STEP = {"easy": 256, "hard": 512}
# hard per-rollout wall-clock timeout, seconds (logged; generous, diagnostic)
WALL_TIMEOUT_S = {"easy": 300.0, "hard": 600.0}

BENCHMARKS = tuple(FAMILY)


def family(benchmark: str) -> str:
    return FAMILY[benchmark]


def band(benchmark: str) -> str:
    return BAND[benchmark]
