# docs-rag serving scenarios (fake provider, projected cost)

Fake provider: the spans come from real docs-rag pipeline runs over one shared request stream, but the LLM has no real latency or bill. Cost per 1k requests is PROJECTED (observed tokens at list price: claude-sonnet-4.5, claude-haiku-4.5 for cheaper_model, reranker billed as rerank-v3.5); p50/p95 are pipeline compute only; cache hit rates are set by the replay.

| Scenario | requests | $/1k req | Δ cost | p50 ms | p95 ms | Δ p95 | cache hit rate | error rate |
|---|---|---|---|---|---|---|---|---|
| baseline | 666 | 5.60 | +0% | 9 | 15 | +0% | 0% | 0.0% |
| exact_cache | 666 | 3.71 | -34% | 10 | 16 | +5% | 34% | 0.0% |
| semantic_cache | 666 | 2.47 | -56% | 3 | 18 | +17% | 56% | 0.0% |
| cheaper_model | 666 | 1.41 | -75% | 3 | 18 | +20% | 56% | 0.0% |
