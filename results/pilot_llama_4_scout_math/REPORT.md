# REPORT — pilot_llama_4_scout_math

160 rollouts, 20 tasks, 4 cells, model `llama_4_scout`, benchmark `math` (hard).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| BARE | 40 | 0.70 | 0.575 | 0.57 | 0.65 | 0.85 | 662 |
| P+T+M+SR+R | 40 | 0.42 | 0.375 | 0.38 | 0.40 | 0.95 | 959 |
| T | 40 | 0.80 | 0.600 | 0.60 | 0.65 | 0.90 | 659 |
| T+SR+R | 40 | 0.53 | 0.375 | 0.38 | 0.50 | 0.75 | 874 |

Failure modes: answered=98, no_answer=37, step_cap=24, parse_loop=1
Parse failures (retried once each): 150
