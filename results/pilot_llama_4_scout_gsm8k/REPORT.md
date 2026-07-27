# REPORT — pilot_llama_4_scout_gsm8k

160 rollouts, 20 tasks, 4 cells, model `llama_4_scout`, benchmark `gsm8k` (easy).

| config | n | answered | y_mean | em | pass@k | c_out | tokens_out |
|---|---:|---:|---:|---:|---:|---:|---:|
| BARE | 40 | 0.88 | 0.825 | 0.82 | 0.85 | 0.95 | 239 |
| P+T+M+SR+R | 40 | 0.65 | 0.650 | 0.65 | 0.75 | 0.80 | 532 |
| T | 40 | 0.93 | 0.900 | 0.90 | 0.90 | 1.00 | 176 |
| T+SR+R | 40 | 0.65 | 0.650 | 0.65 | 0.70 | 0.90 | 271 |

Failure modes: answered=124, step_cap=18, no_answer=15, parse_loop=3
Parse failures (retried once each): 102
