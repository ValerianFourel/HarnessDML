# REPORT — pilot_gemma_4_26b_a4b_math

160 rollouts, 20 tasks, 4 cells, model `gemma_4_26b_a4b`, benchmark `math` (hard).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| BARE | 40 | 0.65 | 0.475 | 0.47 | 0.50 | 0.95 | 873 |
| P+T+M+SR+R | 40 | 0.33 | 0.175 | 0.17 | 0.35 | 0.65 | 1155 |
| T | 40 | 0.65 | 0.500 | 0.50 | 0.50 | 1.00 | 750 |
| T+SR+R | 40 | 0.47 | 0.375 | 0.38 | 0.45 | 0.85 | 814 |

Failure modes: answered=84, no_answer=69, parse_loop=7
Parse failures (retried once each): 194
