# REPORT — pilot_llama_3_1_8b_musique

160 rollouts, 20 tasks, 4 cells, model `llama_3_1_8b`, benchmark `musique` (hard).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| BARE | 40 | 0.53 | 0.328 | 0.25 | 0.30 | 0.90 | 122 |
| P+T+M+SR+R | 40 | 0.20 | 0.163 | 0.15 | 0.25 | 0.80 | 921 |
| T | 40 | 0.03 | 0.013 | 0.00 | 0.00 | 1.00 | 86 |
| T+SR+R | 40 | 0.38 | 0.168 | 0.10 | 0.15 | 0.90 | 463 |

Failure modes: step_cap=92, answered=45, parse_loop=23
Parse failures (retried once each): 70
