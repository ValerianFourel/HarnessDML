# REPORT — pilot_mistral_small_3_2_24b_math

160 rollouts, 20 tasks, 4 cells, model `mistral_small_3_2_24b`, benchmark `math` (hard).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| BARE | 40 | 0.55 | 0.400 | 0.40 | 0.45 | 0.90 | 570 |
| P+T+M+SR+R | 40 | 0.33 | 0.150 | 0.15 | 0.20 | 0.90 | 1181 |
| T | 40 | 0.55 | 0.300 | 0.30 | 0.40 | 0.80 | 654 |
| T+SR+R | 40 | 0.50 | 0.225 | 0.23 | 0.40 | 0.65 | 797 |

Failure modes: answered=77, step_cap=65, parse_loop=16, no_answer=2
Parse failures (retried once each): 94
