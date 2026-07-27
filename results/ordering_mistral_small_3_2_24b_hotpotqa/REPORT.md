# REPORT — ordering_mistral_small_3_2_24b_hotpotqa

3000 rollouts, 100 tasks, 6 cells, model `mistral_small_3_2_24b`, benchmark `hotpotqa` (easy).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| P+T+M+SR+R | 500 | 0.35 | 0.208 | 0.14 | 0.27 | 0.82 | 412 |
| P+T+M+SR+R | 500 | 0.66 | 0.432 | 0.30 | 0.36 | 0.91 | 303 |
| T | 500 | 0.41 | 0.246 | 0.17 | 0.19 | 0.96 | 46 |
| T | 500 | 0.41 | 0.249 | 0.17 | 0.18 | 0.97 | 45 |
| T+SR+R | 500 | 0.54 | 0.350 | 0.25 | 0.28 | 0.96 | 128 |
| T+SR+R | 500 | 0.19 | 0.123 | 0.07 | 0.13 | 0.92 | 238 |

Failure modes: step_cap=1720, answered=1280
Parse failures (retried once each): 1181
