# REPORT — pilot_mistral_small_3_2_24b_gsm8k

160 rollouts, 20 tasks, 4 cells, model `mistral_small_3_2_24b`, benchmark `gsm8k` (easy).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| BARE | 40 | 1.00 | 0.875 | 0.88 | 0.90 | 0.95 | 221 |
| P+T+M+SR+R | 40 | 0.68 | 0.625 | 0.62 | 0.70 | 0.85 | 606 |
| T | 40 | 0.97 | 0.575 | 0.57 | 0.60 | 0.95 | 82 |
| T+SR+R | 40 | 0.57 | 0.550 | 0.55 | 0.65 | 0.80 | 288 |

Failure modes: answered=129, step_cap=31
Parse failures (retried once each): 44
