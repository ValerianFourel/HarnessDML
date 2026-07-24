# REPORT — pilot_ministral_3_3b_gsm8k

160 rollouts, 20 tasks, 4 cells, model `ministral_3_3b`, benchmark `gsm8k` (easy).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| BARE | 40 | 0.75 | 0.700 | 0.70 | 0.75 | 0.90 | 241 |
| P+T+M+SR+R | 40 | 0.30 | 0.225 | 0.23 | 0.35 | 0.75 | 548 |
| T | 40 | 0.72 | 0.475 | 0.47 | 0.60 | 0.75 | 225 |
| T+SR+R | 40 | 0.62 | 0.575 | 0.57 | 0.75 | 0.65 | 457 |

Failure modes: answered=96, step_cap=44, parse_loop=20
Parse failures (retried once each): 121
