# REPORT — temp0_mistral_small_3_2_24b_hotpotqa

1200 rollouts, 100 tasks, 4 cells, model `mistral_small_3_2_24b`, benchmark `hotpotqa` (easy).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| BARE | 300 | 1.00 | 0.370 | 0.27 | 0.28 | 0.98 | 124 |
| P+T+M+SR+R | 300 | 0.57 | 0.341 | 0.20 | 0.23 | 0.96 | 506 |
| T | 300 | 0.41 | 0.251 | 0.18 | 0.18 | 0.99 | 44 |
| T+SR+R | 300 | 0.18 | 0.086 | 0.05 | 0.06 | 0.97 | 239 |

Failure modes: answered=646, step_cap=554
Parse failures (retried once each): 553
