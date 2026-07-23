# REPORT — smoke_live_gpt_oss_20b_gsm8k

20 rollouts, 5 tasks, 2 cells, model `gpt_oss_20b`, benchmark `gsm8k` (easy).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| BARE | 10 | 0.80 | 0.800 | 0.80 | 0.80 | 1.00 | 414 |
| T | 10 | 0.50 | 0.500 | 0.50 | 0.60 | 0.80 | 426 |

Failure modes: answered=13, no_answer=7
Parse failures (retried once each): 20

API-error attempts logged (not in the panel; retried on resume): 20
