# REPORT — pilot_qwen_3_6_27b_math

160 rollouts, 20 tasks, 4 cells, model `qwen_3_6_27b`, benchmark `math` (hard).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| BARE | 40 | 0.40 | 0.300 | 0.30 | 0.30 | 1.00 | 749 |
| P+T+M+SR+R | 40 | 0.47 | 0.375 | 0.38 | 0.45 | 0.85 | 1273 |
| T | 40 | 0.62 | 0.500 | 0.50 | 0.50 | 1.00 | 854 |
| T+SR+R | 40 | 0.72 | 0.525 | 0.53 | 0.55 | 0.95 | 964 |

Failure modes: answered=89, step_cap=44, no_answer=21, parse_loop=6
Parse failures (retried once each): 215
