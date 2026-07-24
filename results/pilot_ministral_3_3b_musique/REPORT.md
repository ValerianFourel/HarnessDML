# REPORT — pilot_ministral_3_3b_musique

160 rollouts, 20 tasks, 4 cells, model `ministral_3_3b`, benchmark `musique` (hard).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| BARE | 40 | 0.95 | 0.161 | 0.10 | 0.10 | 1.00 | 92 |
| P+T+M+SR+R | 40 | 0.62 | 0.214 | 0.12 | 0.15 | 0.95 | 940 |
| T | 40 | 0.35 | 0.222 | 0.15 | 0.25 | 0.80 | 91 |
| T+SR+R | 40 | 0.60 | 0.171 | 0.10 | 0.20 | 0.80 | 491 |

Failure modes: answered=101, step_cap=55, parse_loop=4
Parse failures (retried once each): 69
