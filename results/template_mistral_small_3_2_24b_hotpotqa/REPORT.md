# REPORT — template_mistral_small_3_2_24b_hotpotqa

1500 rollouts, 50 tasks, 6 cells, model `mistral_small_3_2_24b`, benchmark `hotpotqa` (easy).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| P+T+M+SR+R | 250 | 0.58 | 0.351 | 0.18 | 0.24 | 0.88 | 461 |
| P+T+M+SR+R | 250 | 0.18 | 0.109 | 0.07 | 0.14 | 0.92 | 312 |
| T | 250 | 0.36 | 0.189 | 0.12 | 0.12 | 1.00 | 50 |
| T | 250 | 0.43 | 0.243 | 0.16 | 0.20 | 0.94 | 46 |
| T+SR+R | 250 | 0.03 | 0.018 | 0.01 | 0.02 | 0.98 | 196 |
| T+SR+R | 250 | 0.12 | 0.074 | 0.04 | 0.12 | 0.92 | 246 |

Failure modes: step_cap=1075, answered=425
Parse failures (retried once each): 1374
