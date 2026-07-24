# REPORT — pilot_qwen_3_5_9b_hotpotqa

160 rollouts, 20 tasks, 4 cells, model `qwen_3_5_9b`, benchmark `hotpotqa` (easy).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| BARE | 40 | 1.00 | 0.144 | 0.05 | 0.05 | 1.00 | 174 |
| P+T+M+SR+R | 40 | 0.53 | 0.275 | 0.15 | 0.20 | 0.90 | 553 |
| T | 40 | 0.70 | 0.385 | 0.23 | 0.25 | 0.95 | 45 |
| T+SR+R | 40 | 0.55 | 0.255 | 0.15 | 0.15 | 1.00 | 339 |

Failure modes: answered=111, step_cap=32, no_answer=12, parse_loop=5
Parse failures (retried once each): 80
