# REPORT — pilot_qwen_3_6_27b_gsm8k

160 rollouts, 20 tasks, 4 cells, model `qwen_3_6_27b`, benchmark `gsm8k` (easy).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| BARE | 40 | 0.60 | 0.500 | 0.50 | 0.50 | 1.00 | 263 |
| P+T+M+SR+R | 40 | 0.45 | 0.450 | 0.45 | 0.55 | 0.80 | 687 |
| T | 40 | 0.85 | 0.750 | 0.75 | 0.75 | 1.00 | 290 |
| T+SR+R | 40 | 0.75 | 0.750 | 0.75 | 0.75 | 1.00 | 400 |

Failure modes: answered=106, step_cap=36, parse_loop=16, no_answer=2
Parse failures (retried once each): 92
