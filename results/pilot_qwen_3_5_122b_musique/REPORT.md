# REPORT — pilot_qwen_3_5_122b_musique

160 rollouts, 20 tasks, 4 cells, model `qwen_3_5_122b`, benchmark `musique` (hard).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| BARE | 40 | 1.00 | 0.646 | 0.55 | 0.60 | 0.90 | 215 |
| P+T+M+SR+R | 40 | 0.53 | 0.479 | 0.42 | 0.45 | 0.95 | 888 |
| T | 40 | 0.57 | 0.528 | 0.42 | 0.45 | 0.95 | 56 |
| T+SR+R | 40 | 0.47 | 0.426 | 0.35 | 0.40 | 0.90 | 471 |

Failure modes: answered=103, step_cap=57
Parse failures (retried once each): 151
