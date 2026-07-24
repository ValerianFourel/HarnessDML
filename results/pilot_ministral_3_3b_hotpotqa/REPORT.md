# REPORT — pilot_ministral_3_3b_hotpotqa

160 rollouts, 20 tasks, 4 cells, model `ministral_3_3b`, benchmark `hotpotqa` (easy).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| BARE | 40 | 0.88 | 0.161 | 0.12 | 0.15 | 0.95 | 141 |
| P+T+M+SR+R | 40 | 0.25 | 0.088 | 0.03 | 0.05 | 0.95 | 546 |
| T | 40 | 0.23 | 0.026 | 0.00 | 0.00 | 1.00 | 71 |
| T+SR+R | 40 | 0.17 | 0.084 | 0.05 | 0.10 | 0.90 | 331 |

Failure modes: step_cap=94, answered=61, parse_loop=5
Parse failures (retried once each): 68
