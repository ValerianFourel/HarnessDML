# REPORT — pilot_qwen_3_5_122b_gsm8k

160 rollouts, 20 tasks, 4 cells, model `qwen_3_5_122b`, benchmark `gsm8k` (easy).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| BARE | 40 | 1.00 | 0.750 | 0.75 | 0.75 | 1.00 | 258 |
| P+T+M+SR+R | 40 | 0.47 | 0.425 | 0.42 | 0.50 | 0.85 | 625 |
| T | 40 | 1.00 | 0.875 | 0.88 | 0.90 | 0.95 | 55 |
| T+SR+R | 40 | 0.90 | 0.850 | 0.85 | 0.85 | 1.00 | 434 |

Failure modes: answered=135, step_cap=25
Parse failures (retried once each): 76
