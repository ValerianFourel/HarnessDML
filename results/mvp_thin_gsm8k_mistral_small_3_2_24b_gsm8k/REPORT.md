# REPORT — mvp_thin_gsm8k_mistral_small_3_2_24b_gsm8k

28380 rollouts, 1319 tasks, 4 cells, model `mistral_small_3_2_24b`, benchmark `gsm8k` (easy).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| BARE | 7095 | 1.00 | 0.844 | 0.84 | 0.89 | 0.93 | 231 |
| P+T+M+SR+R | 7095 | 0.66 | 0.618 | 0.62 | 0.70 | 0.88 | 600 |
| T | 7095 | 0.89 | 0.735 | 0.74 | 0.80 | 0.89 | 91 |
| T+SR+R | 7095 | 0.59 | 0.543 | 0.54 | 0.69 | 0.78 | 301 |

Failure modes: answered=22228, step_cap=6115, parse_loop=28, no_answer=9
Parse failures (retried once each): 8089
