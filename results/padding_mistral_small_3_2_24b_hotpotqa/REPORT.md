# REPORT — padding_mistral_small_3_2_24b_hotpotqa

3000 rollouts, 100 tasks, 6 cells, model `mistral_small_3_2_24b`, benchmark `hotpotqa` (easy).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| M | 500 | 0.98 | 0.348 | 0.24 | 0.27 | 0.96 | 117 |
| P | 500 | 0.99 | 0.328 | 0.22 | 0.23 | 0.97 | 119 |
| P+T+M+SR+R | 500 | 0.99 | 0.317 | 0.23 | 0.26 | 0.95 | 108 |
| R | 500 | 0.99 | 0.336 | 0.22 | 0.26 | 0.95 | 122 |
| SR | 500 | 0.99 | 0.352 | 0.24 | 0.27 | 0.95 | 117 |
| T | 500 | 1.00 | 0.333 | 0.22 | 0.25 | 0.95 | 109 |

Failure modes: answered=2969, parse_loop=31
Parse failures (retried once each): 114
