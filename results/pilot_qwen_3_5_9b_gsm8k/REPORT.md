# REPORT — pilot_qwen_3_5_9b_gsm8k

160 rollouts, 20 tasks, 4 cells, model `qwen_3_5_9b`, benchmark `gsm8k` (easy).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| BARE | 40 | 1.00 | 0.725 | 0.72 | 0.75 | 0.95 | 252 |
| P+T+M+SR+R | 40 | 0.42 | 0.400 | 0.40 | 0.55 | 0.70 | 587 |
| T | 40 | 1.00 | 0.575 | 0.57 | 0.60 | 0.95 | 55 |
| T+SR+R | 40 | 0.80 | 0.700 | 0.70 | 0.75 | 0.90 | 408 |

Failure modes: answered=129, no_answer=15, parse_loop=10, step_cap=6
Parse failures (retried once each): 112
