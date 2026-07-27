# REPORT — pilot_gemma_4_e4b_math

160 rollouts, 20 tasks, 4 cells, model `gemma_4_e4b`, benchmark `math` (hard).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| BARE | 40 | 0.62 | 0.250 | 0.25 | 0.25 | 1.00 | 728 |
| P+T+M+SR+R | 40 | 0.50 | 0.400 | 0.40 | 0.45 | 0.90 | 1495 |
| T | 40 | 0.68 | 0.525 | 0.53 | 0.55 | 0.95 | 923 |
| T+SR+R | 40 | 0.57 | 0.450 | 0.45 | 0.50 | 0.90 | 1017 |

Failure modes: answered=95, no_answer=36, step_cap=15, parse_loop=14
Parse failures (retried once each): 201
