# REPORT — mvp_headline_topup_mistral_small_3_2_24b_math

4000 rollouts, 100 tasks, 4 cells, model `mistral_small_3_2_24b`, benchmark `math` (hard).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| BARE | 1000 | 0.50 | 0.329 | 0.33 | 0.42 | 0.88 | 541 |
| P+T+M+SR+R | 1000 | 0.37 | 0.198 | 0.20 | 0.38 | 0.84 | 1153 |
| T | 1000 | 0.68 | 0.333 | 0.33 | 0.60 | 0.68 | 639 |
| T+SR+R | 1000 | 0.41 | 0.211 | 0.21 | 0.47 | 0.73 | 727 |

Failure modes: answered=1956, step_cap=1532, parse_loop=441, no_answer=71
Parse failures (retried once each): 2407
