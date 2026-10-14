# Judge calibration

Generated 2026-10-14T20:32:50+00:00 by `scripts/calibrate_judge.py` (judge: **lexical**, provider: fake, 54 answered rows in `evals\human_labels.jsonl`).

| criterion | kappa | agreement | labelled n | position-swap consistency | mean len PASS / FAIL | length bias r |
|---|---|---|---|---|---|---|
| faithfulness | 1.000 | 1.000 | 23 | 1.000 | 182.4 / 0.0 | +0.000 |
| answer_relevance | 0.777 | 0.957 | 23 | 1.000 | 183.8 / 147.0 | +0.061 |

Interpretation: kappa above 0.6 is substantial agreement, 0.4-0.6 moderate, below 0.4 the judge should not be trusted for that criterion. Position-swap consistency should be close to 1.0. A length-bias correlation above +0.3 means the judge rewards verbosity. Kappa is undefined when every label is identical; it is reported as 1.0 only when the judge also agrees on every row.

## Disagreements

- `h-0009` (answer_relevance) human=False judge=True: What is the availability SLO for a tier-1 service? -> 'Every tier-1 and tier-2 service defines at least an availability SLO and a latency SLO in its `service.yaml`. [935e2f5573]'
