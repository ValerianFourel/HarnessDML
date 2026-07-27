# REPORT — pilot_gemma_4_e4b_gsm8k

160 rollouts, 20 tasks, 4 cells, model `gemma_4_e4b`, benchmark `gsm8k` (easy).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| BARE | 40 | 1.00 | 0.725 | 0.72 | 0.80 | 0.85 | 254 |
| P+T+M+SR+R | 40 | 0.42 | 0.400 | 0.40 | 0.50 | 0.80 | 672 |
| T | 40 | 0.80 | 0.775 | 0.78 | 0.85 | 0.85 | 315 |
| T+SR+R | 40 | 0.72 | 0.675 | 0.68 | 0.70 | 0.95 | 471 |

Failure modes: answered=118, step_cap=29, no_answer=9, parse_loop=4
Parse failures (retried once each): 90
