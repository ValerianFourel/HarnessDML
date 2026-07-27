# REPORT — pilot_llama_4_scout_hotpotqa

160 rollouts, 20 tasks, 4 cells, model `llama_4_scout`, benchmark `hotpotqa` (easy).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| BARE | 40 | 0.93 | 0.314 | 0.20 | 0.20 | 1.00 | 110 |
| P+T+M+SR+R | 40 | 0.42 | 0.274 | 0.20 | 0.25 | 0.90 | 664 |
| T | 40 | 0.23 | 0.095 | 0.03 | 0.05 | 0.95 | 49 |
| T+SR+R | 40 | 0.38 | 0.268 | 0.20 | 0.20 | 1.00 | 261 |

Failure modes: answered=78, step_cap=76, parse_loop=5, no_answer=1
Parse failures (retried once each): 83
