# REPORT — pilot_gpt_oss_20b_hotpotqa

160 rollouts, 20 tasks, 4 cells, model `gpt_oss_20b`, benchmark `hotpotqa` (easy).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| BARE | 40 | 0.35 | 0.099 | 0.05 | 0.10 | 0.90 | 468 |
| P+T+M+SR+R | 40 | 0.00 | 0.000 | 0.00 | 0.00 | 1.00 | 285 |
| T | 40 | 0.05 | 0.006 | 0.00 | 0.00 | 1.00 | 240 |
| T+SR+R | 40 | 0.00 | 0.000 | 0.00 | 0.00 | 1.00 | 243 |

Failure modes: no_answer=144, answered=16
Parse failures (retried once each): 297
