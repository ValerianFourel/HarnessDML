# REPORT — pilot_mistral_small_3_2_24b_musique

160 rollouts, 20 tasks, 4 cells, model `mistral_small_3_2_24b`, benchmark `musique` (hard).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| BARE | 40 | 1.00 | 0.460 | 0.40 | 0.40 | 1.00 | 82 |
| P+T+M+SR+R | 40 | 0.62 | 0.427 | 0.35 | 0.35 | 1.00 | 729 |
| T | 40 | 0.62 | 0.469 | 0.42 | 0.45 | 0.95 | 55 |
| T+SR+R | 40 | 0.42 | 0.372 | 0.35 | 0.45 | 0.80 | 381 |

Failure modes: answered=107, step_cap=53
Parse failures (retried once each): 86
