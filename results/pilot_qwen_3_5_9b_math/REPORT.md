# REPORT — pilot_qwen_3_5_9b_math

160 rollouts, 20 tasks, 4 cells, model `qwen_3_5_9b`, benchmark `math` (hard).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| BARE | 40 | 0.50 | 0.325 | 0.33 | 0.35 | 0.95 | 515 |
| P+T+M+SR+R | 40 | 0.47 | 0.400 | 0.40 | 0.45 | 0.90 | 1187 |
| T | 40 | 0.82 | 0.225 | 0.23 | 0.25 | 0.95 | 595 |
| T+SR+R | 40 | 0.70 | 0.500 | 0.50 | 0.55 | 0.90 | 997 |

Failure modes: answered=100, no_answer=26, parse_loop=20, step_cap=14
Parse failures (retried once each): 175
