# REPORT — pilot_qwen_3_6_27b_hotpotqa

160 rollouts, 20 tasks, 4 cells, model `qwen_3_6_27b`, benchmark `hotpotqa` (easy).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| BARE | 40 | 0.90 | 0.344 | 0.15 | 0.15 | 1.00 | 97 |
| P+T+M+SR+R | 40 | 0.65 | 0.489 | 0.35 | 0.35 | 1.00 | 488 |
| T | 40 | 0.50 | 0.370 | 0.28 | 0.30 | 0.95 | 38 |
| T+SR+R | 40 | 0.33 | 0.182 | 0.10 | 0.15 | 0.90 | 358 |

Failure modes: answered=95, step_cap=61, parse_loop=4
Parse failures (retried once each): 73
