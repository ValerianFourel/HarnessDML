# REPORT — pilot_gemma_4_e4b_musique

160 rollouts, 20 tasks, 4 cells, model `gemma_4_e4b`, benchmark `musique` (hard).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| BARE | 40 | 1.00 | 0.236 | 0.15 | 0.15 | 1.00 | 91 |
| P+T+M+SR+R | 40 | 0.35 | 0.212 | 0.20 | 0.25 | 0.90 | 723 |
| T | 40 | 0.50 | 0.375 | 0.35 | 0.35 | 1.00 | 79 |
| T+SR+R | 40 | 0.17 | 0.125 | 0.12 | 0.15 | 0.95 | 379 |

Failure modes: answered=81, step_cap=55, parse_loop=17, no_answer=7
Parse failures (retried once each): 149
