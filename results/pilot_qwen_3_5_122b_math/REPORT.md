# REPORT — pilot_qwen_3_5_122b_math

160 rollouts, 20 tasks, 4 cells, model `qwen_3_5_122b`, benchmark `math` (hard).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| BARE | 40 | 0.70 | 0.400 | 0.40 | 0.40 | 1.00 | 646 |
| P+T+M+SR+R | 40 | 0.72 | 0.500 | 0.50 | 0.55 | 0.90 | 1376 |
| T | 40 | 0.72 | 0.525 | 0.53 | 0.60 | 0.85 | 803 |
| T+SR+R | 40 | 0.82 | 0.600 | 0.60 | 0.60 | 1.00 | 1053 |

Failure modes: answered=119, step_cap=24, no_answer=15, parse_loop=2
Parse failures (retried once each): 190
