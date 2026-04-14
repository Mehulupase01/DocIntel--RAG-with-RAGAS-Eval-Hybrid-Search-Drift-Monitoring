# Retrieval

## Strategies
- `vector_only`: embed the query, rank chunks by pgvector cosine similarity, and return `vector_score` only.
- `bm25_only`: rank chunks by `ts_rank_cd(tsv, plainto_tsquery('english', :q))` and return `bm25_score` only.
- `hybrid`: run BM25 and vector search independently, fuse the ranked lists with Reciprocal Rank Fusion, and return `bm25_score`, `vector_score`, and `fused_score`.
- `hybrid_reranked`: run the hybrid path first, then rerank the fused candidate set with the cross-encoder and return all four score components.

## Search Contract
- Endpoint: `POST /api/v1/search`
- Auth: requires `X-API-Key`
- Request fields:
  - `query`
  - `strategy`
  - `top_k`
  - `rerank_top_n`
  - `rrf_k`
  - optional `document_ids`
- Response fields:
  - `query_id`
  - `results[]` with chunk identity, document metadata, rank, and the score components relevant to the selected strategy

## RRF
- Formula: `score(d) = sum(1 / (k + rank_i(d)))`
- Default `k`: `60`
- Reason: RRF avoids score normalization across BM25 and vector similarity while remaining robust on small corpora.

## Reranker Contract
- Model: `cross-encoder/ms-marco-MiniLM-L-6-v2`
- Input: `(query, chunk_text)` pairs for the fused candidate set
- Output: a reranked list with `rerank_score`
- Retrieval persistence keeps every final ranked chunk together with the score components that were actually used for the selected strategy

## Seeded Benchmark
- CLI: `uv run python -m docintel.tools.benchmark_retrieval --top-k 10`
- Purpose: deterministic regression check that compares all four retrieval strategies on a seeded fixture instead of the live corpus
- Fixture behavior:
  - seeds a temporary synthetic document into Postgres
  - uses controlled query embeddings and reranker scores so strategy behavior is repeatable
  - deletes the fixture after the run so benchmark-only data does not affect production retrieval
