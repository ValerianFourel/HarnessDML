# REPORT — pilot_gpt_oss_20b_gsm8k

158 rollouts, 20 tasks, 4 cells, model `gpt_oss_20b`, benchmark `gsm8k` (easy).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| BARE | 40 | 0.78 | 0.775 | 0.78 | 0.85 | 0.85 | 366 |
| P+T+M+SR+R | 38 | 0.61 | 0.605 | 0.61 | 0.60 | 1.00 | 447 |
| T | 40 | 0.62 | 0.625 | 0.62 | 0.70 | 0.85 | 372 |
| T+SR+R | 40 | 0.55 | 0.550 | 0.55 | 0.65 | 0.80 | 378 |

Failure modes: answered=101, no_answer=57
Parse failures (retried once each): 164

API-error attempts logged (not in the panel; retried on resume): 2
