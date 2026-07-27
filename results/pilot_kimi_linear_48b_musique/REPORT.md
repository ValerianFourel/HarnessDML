# REPORT — pilot_kimi_linear_48b_musique

160 rollouts, 20 tasks, 4 cells, model `kimi_linear_48b`, benchmark `musique` (hard).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| BARE | 40 | 1.00 | 0.483 | 0.40 | 0.45 | 0.90 | 95 |
| P+T+M+SR+R | 40 | 0.25 | 0.215 | 0.20 | 0.25 | 0.90 | 248 |
| T | 40 | 0.70 | 0.449 | 0.38 | 0.50 | 0.75 | 70 |
| T+SR+R | 40 | 0.47 | 0.268 | 0.17 | 0.30 | 0.75 | 315 |

Failure modes: answered=97, step_cap=63
Parse failures (retried once each): 28
