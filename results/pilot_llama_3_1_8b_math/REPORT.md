# REPORT — pilot_llama_3_1_8b_math

160 rollouts, 20 tasks, 4 cells, model `llama_3_1_8b`, benchmark `math` (hard).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| BARE | 40 | 0.55 | 0.300 | 0.30 | 0.35 | 0.90 | 405 |
| P+T+M+SR+R | 40 | 0.07 | 0.050 | 0.05 | 0.10 | 0.90 | 1116 |
| T | 40 | 0.15 | 0.000 | 0.00 | 0.00 | 1.00 | 247 |
| T+SR+R | 40 | 0.55 | 0.075 | 0.07 | 0.10 | 0.95 | 990 |

Failure modes: step_cap=68, answered=53, parse_loop=39
Parse failures (retried once each): 133
