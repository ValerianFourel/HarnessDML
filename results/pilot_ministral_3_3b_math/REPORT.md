# REPORT — pilot_ministral_3_3b_math

160 rollouts, 20 tasks, 4 cells, model `ministral_3_3b`, benchmark `math` (hard).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| BARE | 40 | 0.25 | 0.175 | 0.17 | 0.20 | 0.95 | 662 |
| P+T+M+SR+R | 40 | 0.17 | 0.100 | 0.10 | 0.20 | 0.80 | 1182 |
| T | 40 | 0.42 | 0.000 | 0.00 | 0.00 | 1.00 | 1121 |
| T+SR+R | 40 | 0.47 | 0.250 | 0.25 | 0.35 | 0.80 | 1324 |

Failure modes: parse_loop=77, answered=53, step_cap=30
Parse failures (retried once each): 220
