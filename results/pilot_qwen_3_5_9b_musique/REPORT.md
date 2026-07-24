# REPORT — pilot_qwen_3_5_9b_musique

160 rollouts, 20 tasks, 4 cells, model `qwen_3_5_9b`, benchmark `musique` (hard).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| BARE | 40 | 1.00 | 0.436 | 0.30 | 0.35 | 0.90 | 239 |
| P+T+M+SR+R | 40 | 0.53 | 0.366 | 0.28 | 0.40 | 0.75 | 1236 |
| T | 40 | 0.53 | 0.397 | 0.30 | 0.35 | 0.90 | 60 |
| T+SR+R | 40 | 0.53 | 0.423 | 0.33 | 0.35 | 0.95 | 550 |

Failure modes: answered=103, step_cap=50, no_answer=6, parse_loop=1
Parse failures (retried once each): 91
