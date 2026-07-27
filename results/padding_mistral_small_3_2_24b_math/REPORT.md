# REPORT — padding_mistral_small_3_2_24b_math

3000 rollouts, 100 tasks, 6 cells, model `mistral_small_3_2_24b`, benchmark `math` (hard).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| M | 500 | 0.50 | 0.296 | 0.30 | 0.35 | 0.93 | 547 |
| P | 500 | 0.48 | 0.304 | 0.30 | 0.36 | 0.92 | 511 |
| P+T+M+SR+R | 500 | 0.47 | 0.302 | 0.30 | 0.35 | 0.94 | 505 |
| R | 500 | 0.51 | 0.320 | 0.32 | 0.38 | 0.90 | 523 |
| SR | 500 | 0.50 | 0.304 | 0.30 | 0.37 | 0.91 | 531 |
| T | 500 | 0.50 | 0.316 | 0.32 | 0.36 | 0.90 | 522 |

Failure modes: answered=1478, parse_loop=1358, no_answer=164
Parse failures (retried once each): 3623
