# REPORT — temp0_mistral_small_3_2_24b_math

1200 rollouts, 100 tasks, 4 cells, model `mistral_small_3_2_24b`, benchmark `math` (hard).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| BARE | 300 | 0.52 | 0.343 | 0.34 | 0.36 | 0.97 | 558 |
| P+T+M+SR+R | 300 | 0.40 | 0.200 | 0.20 | 0.27 | 0.89 | 1137 |
| T | 300 | 0.68 | 0.333 | 0.33 | 0.39 | 0.89 | 635 |
| T+SR+R | 300 | 0.44 | 0.250 | 0.25 | 0.34 | 0.85 | 725 |

Failure modes: answered=613, step_cap=438, parse_loop=121, no_answer=28
Parse failures (retried once each): 711
