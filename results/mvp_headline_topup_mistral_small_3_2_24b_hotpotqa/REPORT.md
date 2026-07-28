# REPORT — mvp_headline_topup_mistral_small_3_2_24b_hotpotqa

4000 rollouts, 100 tasks, 4 cells, model `mistral_small_3_2_24b`, benchmark `hotpotqa` (easy).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| BARE | 1000 | 0.99 | 0.375 | 0.28 | 0.31 | 0.93 | 122 |
| P+T+M+SR+R | 1000 | 0.61 | 0.369 | 0.23 | 0.33 | 0.89 | 517 |
| T | 1000 | 0.42 | 0.253 | 0.17 | 0.20 | 0.96 | 45 |
| T+SR+R | 1000 | 0.17 | 0.096 | 0.05 | 0.11 | 0.94 | 242 |

Failure modes: answered=2197, step_cap=1798, parse_loop=5
Parse failures (retried once each): 1807
