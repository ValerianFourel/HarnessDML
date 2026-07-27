# REPORT — pilot_qwen_3_6_27b_musique

160 rollouts, 20 tasks, 4 cells, model `qwen_3_6_27b`, benchmark `musique` (hard).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| BARE | 40 | 0.82 | 0.492 | 0.38 | 0.40 | 0.95 | 176 |
| P+T+M+SR+R | 40 | 0.62 | 0.551 | 0.47 | 0.50 | 0.95 | 842 |
| T | 40 | 0.57 | 0.522 | 0.45 | 0.45 | 1.00 | 54 |
| T+SR+R | 40 | 0.50 | 0.451 | 0.38 | 0.45 | 0.85 | 626 |

Failure modes: answered=101, step_cap=52, parse_loop=7
Parse failures (retried once each): 52
