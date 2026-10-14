### All cases (222)

| variant | recall@5 | recall@20 | precision@5 | MRR | faithfulness | halluc. rate | refusal recall | false refusal | p95 ms | $/1k (projected) |
|---|---|---|---|---|---|---|---|---|---|---|
| naive | 0.991 | 1.000 | 0.346 | 0.964 | 1.000 | 0.009 | 0.750 | 0.014 | 1 | - |
| hybrid | 0.998 | 1.000 | 0.348 | 0.993 | 1.000 | 0.014 | 0.625 | 0.009 | 1 | - |
| reranked | 1.000 | 1.000 | 0.349 | 0.986 | 1.000 | 0.014 | 0.625 | 0.009 | 6 | - |
| final | 1.000 | 1.000 | 0.349 | 0.986 | 1.000 | 0.014 | 0.625 | 0.009 | 11 | - |

### Source: human (23 cases)

| variant | recall@5 | recall@20 | precision@5 | MRR | faithfulness | halluc. rate | refusal recall | false refusal | p95 ms | $/1k (projected) |
|---|---|---|---|---|---|---|---|---|---|---|
| naive | 0.900 | 1.000 | 0.200 | 0.840 | 1.000 | 0.125 | 0.750 | 0.067 | 1 | - |
| hybrid | 0.967 | 1.000 | 0.213 | 0.967 | 1.000 | 0.167 | 0.625 | 0.000 | 1 | - |
| reranked | 1.000 | 1.000 | 0.227 | 0.836 | 1.000 | 0.167 | 0.625 | 0.000 | 5 | - |
| final | 1.000 | 1.000 | 0.227 | 0.836 | 1.000 | 0.167 | 0.625 | 0.000 | 6 | - |

### Source: synthetic (199 cases)

| variant | recall@5 | recall@20 | precision@5 | MRR | faithfulness | halluc. rate | refusal recall | false refusal | p95 ms | $/1k (projected) |
|---|---|---|---|---|---|---|---|---|---|---|
| naive | 0.998 | 1.000 | 0.357 | 0.974 | 1.000 | 0.000 | - | 0.010 | 1 | - |
| hybrid | 1.000 | 1.000 | 0.358 | 0.995 | 1.000 | 0.000 | - | 0.010 | 1 | - |
| reranked | 1.000 | 1.000 | 0.358 | 0.998 | 1.000 | 0.000 | - | 0.010 | 6 | - |
| final | 1.000 | 1.000 | 0.358 | 0.998 | 1.000 | 0.000 | - | 0.010 | 11 | - |
Provider: **fake** (deterministic fake LLM, hashed-bag-of-words embeddings, lexical judge). These numbers describe the plumbing, not a real model: set OPENROUTER_API_KEY and run `make eval` for real numbers.
Synthetic questions are templated from the chunk they target and therefore overstate recall; the `human` rows are the honest ones. `$/1k (projected)` prices the observed token counts at the configured model's list price in pricing.json.
