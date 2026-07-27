# REPORT — pilot_gemma_4_26b_a4b_hotpotqa

160 rollouts, 20 tasks, 4 cells, model `gemma_4_26b_a4b`, benchmark `hotpotqa` (easy).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| BARE | 40 | 0.90 | 0.351 | 0.25 | 0.25 | 1.00 | 201 |
| P+T+M+SR+R | 40 | 0.00 | 0.000 | 0.00 | 0.00 | 1.00 | 438 |
| T | 40 | 0.23 | 0.149 | 0.10 | 0.10 | 1.00 | 93 |
| T+SR+R | 40 | 0.00 | 0.000 | 0.00 | 0.00 | 1.00 | 242 |

Failure modes: step_cap=74, answered=45, parse_loop=33, no_answer=8
Parse failures (retried once each): 238
