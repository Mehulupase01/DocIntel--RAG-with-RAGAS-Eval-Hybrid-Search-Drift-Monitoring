# API

## `POST /api/v1/search`

Searches the ingested corpus and returns ranked chunks with score components for the selected retrieval strategy.

Example request:

```json
{
  "query": "What is a high-risk AI system?",
  "strategy": "hybrid_reranked",
  "top_k": 5
}
```

## `POST /api/v1/answer`

Runs retrieval plus generation, then returns a citation-grounded answer together with the retrieved contexts and extracted citations.

Example request:

```json
{
  "query": "Define high-risk AI system per the EU AI Act",
  "top_k": 6,
  "strategy": "hybrid_reranked",
  "model": "anthropic/claude-haiku-4-5",
  "temperature": 0.0,
  "max_tokens": 1024
}
```

Example response shape:

```json
{
  "query_id": "uuid",
  "answer_id": "uuid",
  "answer": "A high-risk AI system is defined by Article 6 and Annex III.",
  "citations": [
    {
      "ordinal": 1,
      "chunk_id": "uuid",
      "document_id": "uuid",
      "document_title": "EU AI Act",
      "page_start": 12,
      "page_end": 12,
      "section_path": "Article 6",
      "span_text": "A high-risk AI system is defined in Article 6..."
    }
  ],
  "contexts": [],
  "model": "anthropic/claude-haiku-4-5",
  "prompt_tokens": 123,
  "completion_tokens": 45,
  "cost_usd": 0.000348,
  "latency_ms": 812
}
```
