# REPORT — pilot_llama_4_scout_musique

160 rollouts, 20 tasks, 4 cells, model `llama_4_scout`, benchmark `musique` (hard).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| BARE | 40 | 0.95 | 0.429 | 0.35 | 0.35 | 1.00 | 100 |
| P+T+M+SR+R | 40 | 0.60 | 0.375 | 0.33 | 0.40 | 0.85 | 690 |
| T | 40 | 0.30 | 0.283 | 0.25 | 0.30 | 0.90 | 76 |
| T+SR+R | 40 | 0.33 | 0.296 | 0.28 | 0.30 | 0.95 | 377 |

Failure modes: answered=87, step_cap=70, parse_loop=3
Parse failures (retried once each): 57
