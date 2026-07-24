# REPORT — pilot_gpt_oss_20b_musique

160 rollouts, 20 tasks, 4 cells, model `gpt_oss_20b`, benchmark `musique` (hard).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| BARE | 40 | 0.57 | 0.362 | 0.28 | 0.30 | 0.95 | 690 |
| P+T+M+SR+R | 40 | 0.00 | 0.000 | 0.00 | 0.00 | 1.00 | 353 |
| T | 40 | 0.00 | 0.000 | 0.00 | 0.00 | 1.00 | 275 |
| T+SR+R | 40 | 0.00 | 0.000 | 0.00 | 0.00 | 1.00 | 294 |

Failure modes: no_answer=137, answered=23
Parse failures (retried once each): 280
