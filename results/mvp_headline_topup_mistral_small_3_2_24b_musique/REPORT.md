# REPORT — mvp_headline_topup_mistral_small_3_2_24b_musique

4000 rollouts, 100 tasks, 4 cells, model `mistral_small_3_2_24b`, benchmark `musique` (hard).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| BARE | 1000 | 1.00 | 0.258 | 0.16 | 0.23 | 0.92 | 134 |
| P+T+M+SR+R | 1000 | 0.44 | 0.252 | 0.19 | 0.31 | 0.86 | 869 |
| T | 1000 | 0.32 | 0.187 | 0.15 | 0.19 | 0.96 | 60 |
| T+SR+R | 1000 | 0.22 | 0.128 | 0.11 | 0.25 | 0.85 | 384 |

Failure modes: step_cap=2019, answered=1978, parse_loop=3
Parse failures (retried once each): 2224
