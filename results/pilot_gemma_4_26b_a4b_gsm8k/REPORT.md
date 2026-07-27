# REPORT — pilot_gemma_4_26b_a4b_gsm8k

160 rollouts, 20 tasks, 4 cells, model `gemma_4_26b_a4b`, benchmark `gsm8k` (easy).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| BARE | 40 | 0.65 | 0.650 | 0.65 | 0.80 | 0.70 | 403 |
| P+T+M+SR+R | 40 | 0.45 | 0.450 | 0.45 | 0.60 | 0.70 | 615 |
| T | 40 | 0.88 | 0.875 | 0.88 | 0.90 | 0.95 | 364 |
| T+SR+R | 40 | 0.78 | 0.775 | 0.78 | 0.80 | 0.95 | 534 |

Failure modes: answered=110, no_answer=35, step_cap=14, parse_loop=1
Parse failures (retried once each): 113
