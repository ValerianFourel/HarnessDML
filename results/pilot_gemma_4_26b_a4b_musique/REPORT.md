# REPORT — pilot_gemma_4_26b_a4b_musique

160 rollouts, 20 tasks, 4 cells, model `gemma_4_26b_a4b`, benchmark `musique` (hard).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| BARE | 40 | 1.00 | 0.522 | 0.35 | 0.40 | 0.90 | 193 |
| P+T+M+SR+R | 40 | 0.23 | 0.225 | 0.23 | 0.25 | 0.95 | 697 |
| T | 40 | 0.38 | 0.362 | 0.35 | 0.40 | 0.90 | 189 |
| T+SR+R | 40 | 0.10 | 0.100 | 0.10 | 0.10 | 1.00 | 344 |

Failure modes: answered=68, step_cap=55, parse_loop=31, no_answer=6
Parse failures (retried once each): 295
