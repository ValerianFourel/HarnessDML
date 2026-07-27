# REPORT — pilot_llama_3_1_8b_hotpotqa

160 rollouts, 20 tasks, 4 cells, model `llama_3_1_8b`, benchmark `hotpotqa` (easy).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| BARE | 40 | 0.45 | 0.187 | 0.15 | 0.15 | 1.00 | 145 |
| P+T+M+SR+R | 40 | 0.00 | 0.000 | 0.00 | 0.00 | 1.00 | 587 |
| T | 40 | 0.00 | 0.000 | 0.00 | 0.00 | 1.00 | 67 |
| T+SR+R | 40 | 0.25 | 0.106 | 0.03 | 0.05 | 0.95 | 297 |

Failure modes: step_cap=109, answered=28, parse_loop=23
Parse failures (retried once each): 75
