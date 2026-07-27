# REPORT — pilot_kimi_linear_48b_hotpotqa

160 rollouts, 20 tasks, 4 cells, model `kimi_linear_48b`, benchmark `hotpotqa` (easy).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| BARE | 40 | 0.97 | 0.199 | 0.15 | 0.15 | 1.00 | 107 |
| P+T+M+SR+R | 40 | 0.35 | 0.224 | 0.12 | 0.15 | 0.95 | 213 |
| T | 40 | 0.60 | 0.234 | 0.10 | 0.15 | 0.90 | 58 |
| T+SR+R | 40 | 0.40 | 0.149 | 0.12 | 0.20 | 0.85 | 374 |

Failure modes: answered=93, step_cap=66, parse_loop=1
Parse failures (retried once each): 48
