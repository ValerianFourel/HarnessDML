# REPORT — mvp_thin_gsm8k_mistral_small_3_2_24b_gsm8k

2000 rollouts, 100 tasks, 4 cells, model `mistral_small_3_2_24b`, benchmark `gsm8k` (easy).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| BARE | 500 | 1.00 | 0.846 | 0.85 | 0.90 | 0.94 | 230 |
| P+T+M+SR+R | 500 | 0.65 | 0.610 | 0.61 | 0.68 | 0.88 | 592 |
| T | 500 | 0.91 | 0.740 | 0.74 | 0.82 | 0.87 | 86 |
| T+SR+R | 500 | 0.60 | 0.556 | 0.56 | 0.68 | 0.81 | 303 |

Failure modes: answered=1580, step_cap=419, parse_loop=1
Parse failures (retried once each): 571
