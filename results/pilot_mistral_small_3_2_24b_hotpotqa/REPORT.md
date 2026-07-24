# REPORT — pilot_mistral_small_3_2_24b_hotpotqa

86 rollouts, 20 tasks, 4 cells, model `mistral_small_3_2_24b`, benchmark `hotpotqa` (easy).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| BARE | 21 | 1.00 | 0.141 | 0.05 | 0.07 | 1.00 | 111 |
| P+T+M+SR+R | 21 | 0.71 | 0.374 | 0.19 | 0.15 | 1.00 | 508 |
| T | 23 | 0.35 | 0.138 | 0.04 | 0.06 | 1.00 | 41 |
| T+SR+R | 21 | 0.14 | 0.059 | 0.00 | 0.00 | 1.00 | 271 |

Failure modes: answered=47, step_cap=39
Parse failures (retried once each): 31
