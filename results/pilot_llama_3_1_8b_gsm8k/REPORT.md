# REPORT — pilot_llama_3_1_8b_gsm8k

160 rollouts, 20 tasks, 4 cells, model `llama_3_1_8b`, benchmark `gsm8k` (easy).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| BARE | 40 | 0.90 | 0.850 | 0.85 | 0.90 | 0.90 | 184 |
| P+T+M+SR+R | 40 | 0.25 | 0.225 | 0.23 | 0.25 | 0.95 | 533 |
| T | 40 | 0.30 | 0.175 | 0.17 | 0.20 | 0.95 | 74 |
| T+SR+R | 40 | 0.80 | 0.500 | 0.50 | 0.65 | 0.70 | 371 |

Failure modes: answered=90, step_cap=64, parse_loop=6
Parse failures (retried once each): 55
