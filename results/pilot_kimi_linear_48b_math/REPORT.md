# REPORT — pilot_kimi_linear_48b_math

160 rollouts, 20 tasks, 4 cells, model `kimi_linear_48b`, benchmark `math` (hard).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| BARE | 40 | 0.55 | 0.400 | 0.40 | 0.45 | 0.90 | 651 |
| P+T+M+SR+R | 40 | 0.60 | 0.400 | 0.40 | 0.50 | 0.80 | 1019 |
| T | 40 | 0.60 | 0.350 | 0.35 | 0.40 | 0.90 | 522 |
| T+SR+R | 40 | 0.53 | 0.400 | 0.40 | 0.40 | 1.00 | 664 |

Failure modes: answered=91, step_cap=33, no_answer=20, parse_loop=16
Parse failures (retried once each): 159
