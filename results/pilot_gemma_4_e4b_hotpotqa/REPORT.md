# REPORT — pilot_gemma_4_e4b_hotpotqa

160 rollouts, 20 tasks, 4 cells, model `gemma_4_e4b`, benchmark `hotpotqa` (easy).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| BARE | 40 | 0.88 | 0.178 | 0.10 | 0.10 | 1.00 | 70 |
| P+T+M+SR+R | 40 | 0.28 | 0.194 | 0.17 | 0.20 | 0.95 | 579 |
| T | 40 | 0.33 | 0.138 | 0.03 | 0.05 | 0.95 | 49 |
| T+SR+R | 40 | 0.07 | 0.075 | 0.07 | 0.10 | 0.95 | 274 |

Failure modes: step_cap=67, answered=62, parse_loop=27, no_answer=4
Parse failures (retried once each): 140
