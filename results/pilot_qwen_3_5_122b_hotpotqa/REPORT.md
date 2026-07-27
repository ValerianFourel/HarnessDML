# REPORT — pilot_qwen_3_5_122b_hotpotqa

160 rollouts, 20 tasks, 4 cells, model `qwen_3_5_122b`, benchmark `hotpotqa` (easy).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| BARE | 40 | 1.00 | 0.431 | 0.25 | 0.25 | 1.00 | 167 |
| P+T+M+SR+R | 40 | 0.62 | 0.478 | 0.35 | 0.45 | 0.80 | 514 |
| T | 40 | 0.62 | 0.453 | 0.30 | 0.35 | 0.90 | 54 |
| T+SR+R | 40 | 0.17 | 0.123 | 0.07 | 0.10 | 0.95 | 336 |

Failure modes: answered=97, step_cap=63
Parse failures (retried once each): 121
