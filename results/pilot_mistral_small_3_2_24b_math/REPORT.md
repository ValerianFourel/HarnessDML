# REPORT — pilot_mistral_small_3_2_24b_math

129 rollouts, 20 tasks, 4 cells, model `mistral_small_3_2_24b`, benchmark `math` (hard).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| BARE | 33 | 0.55 | 0.394 | 0.39 | 0.40 | 0.95 | 569 |
| P+T+M+SR+R | 31 | 0.23 | 0.097 | 0.10 | 0.17 | 0.89 | 1222 |
| T | 32 | 0.59 | 0.312 | 0.31 | 0.37 | 0.84 | 581 |
| T+SR+R | 33 | 0.52 | 0.242 | 0.24 | 0.37 | 0.79 | 811 |

Failure modes: answered=61, step_cap=53, parse_loop=13, no_answer=2
Parse failures (retried once each): 75
