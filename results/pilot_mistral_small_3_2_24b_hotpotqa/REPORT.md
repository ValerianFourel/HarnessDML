# REPORT — pilot_mistral_small_3_2_24b_hotpotqa

160 rollouts, 20 tasks, 4 cells, model `mistral_small_3_2_24b`, benchmark `hotpotqa` (easy).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| BARE | 40 | 1.00 | 0.204 | 0.12 | 0.15 | 0.95 | 139 |
| P+T+M+SR+R | 40 | 0.57 | 0.270 | 0.10 | 0.10 | 1.00 | 553 |
| T | 40 | 0.38 | 0.183 | 0.10 | 0.10 | 1.00 | 43 |
| T+SR+R | 40 | 0.15 | 0.049 | 0.00 | 0.00 | 1.00 | 269 |

Failure modes: answered=84, step_cap=76
Parse failures (retried once each): 62
