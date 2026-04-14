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
  "model": "minimax/minimax-m2.5:free",
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
  "model": "minimax/minimax-m2.5:free",
  "prompt_tokens": 123,
  "completion_tokens": 45,
  "cost_usd": 0.0,
  "latency_ms": 812
}
```

## `POST /api/v1/eval/runs`

Creates an evaluation run over the versioned fixture and returns `202 Accepted` while the run continues in the background.

Example request:

```json
{
  "suite_version": "v1",
  "retrieval_strategy": "hybrid_reranked",
  "generation_model": "minimax/minimax-m2.5:free",
  "judge_model": "nvidia/nemotron-3-super-120b-a12b:free",
  "fail_fast": false
}
```

## `GET /api/v1/eval/runs`

Returns paginated evaluation runs. Supports `page`, `per_page`, and optional `status`.

## `GET /api/v1/eval/runs/{id}`

Returns one evaluation run by id.

## `GET /api/v1/eval/runs/{id}/cases`

Returns paginated evaluation cases for a run. Supports `page`, `per_page`, and optional `passed`.

## `POST /api/v1/drift/reports`

Generates a one-shot Evidently drift report comparing the current window against the prior reference window and returns the persisted report metadata.

Example request:

```json
{
  "window_days": 7,
  "reference_window_days": 7
}
```

## `GET /api/v1/drift/reports`

Returns paginated drift reports. Supports `page`, `per_page`, and optional `status`.

## `GET /api/v1/drift/reports/{id}`

Returns one drift report by id, including the local `html_url` for the saved artifact.
