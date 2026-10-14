# Chunk size sweep

Generated 2026-10-14T20:18:44+00:00 by `scripts/sweep_chunks.py` (provider: **fake**, hybrid retrieval + fake reranker, 214 questions of which 15 hand-written).

Sizes are word tokens (about 0.75 LLM tokens). A retrieved chunk counts as relevant when it contains the golden answer line, so every configuration is scored by the same questions. With overlap 0 exactly one chunk is relevant per question, which caps precision@5 at 0.2 and context precision at 0.2; with overlap the answer line can fall in two chunks. Compare hit@5, MRR and nDCG across rows, not precision in isolation.

## All in-corpus questions (214)

| size | overlap | chunks | avg tokens | hit@5 | recall@5 | recall@20 | precision@5 | MRR | nDCG@10 | context precision | faithfulness | p95 ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 128 | 0 | 166 | 83.2 | 1.000 | 1.000 | 1.000 | 0.200 | 0.992 | 0.994 | 0.200 | 1.000 | 5 |
| 128 | 32 | 252 | 85.1 | 1.000 | 1.000 | 1.000 | 0.350 | 0.984 | 0.988 | 0.350 | 1.000 | 8 |
| 256 | 0 | 112 | 123.3 | 1.000 | 1.000 | 1.000 | 0.200 | 0.987 | 0.990 | 0.200 | 1.000 | 12 |
| 256 | 32 | 119 | 139.8 | 1.000 | 0.998 | 1.000 | 0.255 | 0.985 | 0.988 | 0.255 | 1.000 | 16 |
| 512 | 0 | 77 | 179.3 | 1.000 | 1.000 | 1.000 | 0.200 | 0.990 | 0.993 | 0.200 | 1.000 | 22 |
| 512 | 32 | 77 | 196.3 | 1.000 | 1.000 | 1.000 | 0.226 | 0.988 | 0.991 | 0.226 | 1.000 | 18 |

## Hand-written questions (15)

| size | overlap | chunks | avg tokens | hit@5 | recall@5 | recall@20 | precision@5 | MRR | nDCG@10 | context precision | faithfulness | p95 ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 128 | 0 | 166 | 83.2 | 1.000 | 1.000 | 1.000 | 0.200 | 0.922 | 0.942 | 0.200 | 1.000 | 5 |
| 128 | 32 | 252 | 85.1 | 1.000 | 1.000 | 1.000 | 0.307 | 0.856 | 0.893 | 0.307 | 1.000 | 5 |
| 256 | 0 | 112 | 123.3 | 1.000 | 1.000 | 1.000 | 0.200 | 0.811 | 0.860 | 0.200 | 1.000 | 14 |
| 256 | 32 | 119 | 139.8 | 1.000 | 0.967 | 1.000 | 0.227 | 0.856 | 0.882 | 0.227 | 1.000 | 12 |
| 512 | 0 | 77 | 179.3 | 1.000 | 1.000 | 1.000 | 0.200 | 0.889 | 0.917 | 0.200 | 1.000 | 22 |
| 512 | 32 | 77 | 196.3 | 1.000 | 1.000 | 1.000 | 0.213 | 0.889 | 0.917 | 0.213 | 1.000 | 17 |

Fake provider: hashed bag-of-words embeddings, BM25, lexical reranker and an extractive fake LLM. Synthetic questions are templated from their target chunk, so they saturate recall on a corpus this small; absolute values are not comparable to a real model. Re-run with a real key for numbers that can drive the choice.
