# REPORT — pilot_kimi_linear_48b_gsm8k

160 rollouts, 20 tasks, 4 cells, model `kimi_linear_48b`, benchmark `gsm8k` (easy).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| BARE | 40 | 0.95 | 0.825 | 0.82 | 0.90 | 0.85 | 158 |
| P+T+M+SR+R | 40 | 0.80 | 0.725 | 0.72 | 0.85 | 0.75 | 358 |
| T | 40 | 1.00 | 0.850 | 0.85 | 0.85 | 1.00 | 159 |
| T+SR+R | 40 | 0.93 | 0.800 | 0.80 | 0.90 | 0.80 | 302 |

Failure modes: answered=147, step_cap=8, parse_loop=3, no_answer=2
Parse failures (retried once each): 53
