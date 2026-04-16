# DocIntel
### Production RAG with RAGAS Evaluation, Hybrid Search, and Drift Monitoring

![Python](https://img.shields.io/badge/Python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Production_API-009688)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791)
![pgvector](https://img.shields.io/badge/pgvector-Hybrid_Search-6E40C9)
![Streamlit](https://img.shields.io/badge/Streamlit-Ops_Dashboard-FF4B4B)
![Docker](https://img.shields.io/badge/Docker-Deployment_Ready-2496ED)
![MIT License](https://img.shields.io/badge/License-MIT-green)

A production-grade AI system for answering complex regulatory questions over the EU AI Act with cited evidence, measurable quality, hybrid retrieval, automated evaluation, and operational monitoring.

Think of it as an explainable document intelligence platform rather than a PDF chatbot. It ingests a long legal document, indexes it intelligently, retrieves the most relevant evidence using both keyword and semantic search, generates citation-grounded answers, scores answer quality with RAGAS, monitors drift with Evidently, and exposes the entire system through an API plus an operations dashboard.

* * *

## Table of Contents

- Short Abstract
- Deep Introduction
- The Entire System Explained
- Core Intelligence Engines
- Quality Validation
- Detailed Deployment Guide
- Development Notes
- References

* * *

## Short Abstract

When people talk about AI over documents, they usually mean a simple workflow:

1. upload a PDF
2. ask a question
3. get an answer

That is fine for a demo, but it is not enough for any serious environment.

If the document is a regulation, a policy manual, or a legal standard, the user needs far more than a plausible answer. They need to know where the answer came from, whether the retrieval pipeline actually found the right evidence, whether the system is getting better or worse over time, and whether a code change silently damaged quality.

This repository solves exactly that problem.

DocIntel turns the official EU AI Act into a production-shaped retrieval-augmented generation system with five important properties:

- answers are grounded in retrieved evidence
- every answer is citation-aware
- retrieval is hybrid, not vector-only
- quality is measured with RAGAS, not guessed
- operational behavior is visible through metrics, tracing, drift reports, and a dashboard

In practical terms, this means the system can do far more than answer a question like "What is a high-risk AI system?" It can show the supporting passages, log the full retrieval path, benchmark hybrid retrieval against weaker strategies, evaluate performance on a curated question set, and surface degradation before it turns into user-visible failure.

That is what makes this project a full AI system rather than a thin model wrapper.

* * *

## Deep Introduction

### The problem this project solves

Long-form regulatory text is hard for both humans and machines.

Take the EU AI Act as an example. It is not a short article or a tidy FAQ. It is a long, dense, cross-referenced legal document where meaning depends on exact wording, section structure, annexes, and context. A user might ask:

- What qualifies as a high-risk AI system?
- Which practices are prohibited?
- What obligations apply to providers?
- Where do the annexes change the interpretation of an article?

Those questions look simple on the surface, but they are difficult to answer well.

The first difficulty is retrieval. If a system only uses vector search, it may miss the exact article the user expects. If it only uses keyword search, it may miss semantically relevant text phrased differently. If it retrieves too much noise, the language model may answer vaguely or anchor on weak evidence.

The second difficulty is trust. In a legal or compliance setting, "the model said so" is not useful. People want the answer and the evidence behind it.

The third difficulty is operations. A RAG system can look good on day one and quietly degrade afterward because of prompt changes, retrieval changes, model changes, or usage drift. Without evaluation and monitoring, teams often discover the problem only after users lose confidence.

DocIntel is built to solve all three problems together:

- better retrieval
- better answer grounding
- better operational reliability

### What makes this different from a typical AI repo

Most AI repositories show one narrow capability. This one is different in several structural ways.

1. It is a complete operating system for document intelligence, not just a question-answering endpoint.

The system includes ingestion, indexing, retrieval, generation, citations, evaluation, observability, drift reporting, and a read-only dashboard over the same data plane.

2. It uses hybrid retrieval rather than trusting one retrieval method.

Keyword search, semantic search, reciprocal rank fusion, and reranking each solve a different part of the retrieval problem. The system combines them instead of pretending one strategy is enough.

3. It treats evidence as a first-class output.

The answer pipeline is designed so responses can be traced back to chunks, pages, and section paths. This matters a lot more than people think when the underlying corpus is legal or policy-oriented.

4. It treats quality as something to measure continuously.

The repository includes an evaluation harness with RAGAS metrics so quality can be reasoned about systematically rather than anecdotally.

5. It treats drift and monitoring as product concerns, not extras.

Evidently, LangSmith, structured logging, metrics, and dashboard visibility are part of the system design, not afterthoughts.

### Why the EU AI Act is a strong benchmark

The EU AI Act is a particularly good stress test because:

- it is long enough to challenge naive chunking and retrieval
- it is structured enough to reward high-quality citations
- it is legally dense enough to expose hallucinations quickly
- it contains both exact terminology and broader conceptual language

If a system can handle this type of corpus well, that says something meaningful about its architecture.

* * *

## The Entire System Explained

### 1. Ingestion and indexing

The system begins by ingesting the official EU AI Act PDF and converting it into a structured corpus.

This is not handled as one giant blob of text. The ingestion pipeline extracts text page by page, applies structure-aware chunking, preserves document context like page ranges and section paths, and generates dense embeddings for every chunk.

The result is a searchable knowledge base where each chunk is:

- individually addressable
- semantically searchable
- keyword searchable
- traceable back to its source location

That traceability is what later makes high-quality citations possible.

### 2. Retrieval

Once the corpus is indexed, retrieval happens in several stages.

First, the system uses BM25 over PostgreSQL full-text search to capture exact lexical relevance. This is useful when the user asks about specific regulatory phrases or article language.

Second, the system uses pgvector for semantic search so conceptually similar text can be found even when the wording does not match perfectly.

Third, it combines those rankings using Reciprocal Rank Fusion. This lets the system benefit from both lexical precision and semantic recall without depending on incompatible score scales.

Fourth, it reranks the strongest candidates with a cross-encoder so the final evidence set is better aligned with the user question.

The practical outcome is a retrieval stack that is much more robust than a single-mode RAG setup.

### 3. Generation and citations

After retrieval, the system prepares a grounded prompt using the retrieved chunks and sends that context to the language model.

But the important detail is what happens next.

The answer is not returned as free-floating text. The generation path is designed around citation markers so the system can map answer statements back to retrieved evidence. That allows the API to return:

- the answer text
- citation objects
- source chunk ids
- document title
- page start and page end
- section paths

This means the answer layer is not only about fluency. It is about evidence-backed explanation.

### 4. Evaluation

One of the most valuable parts of the project is that it evaluates itself with a proper harness.

Using a curated evaluation fixture and RAGAS, the system scores answer behavior across dimensions such as:

- faithfulness
- context precision
- context recall
- answer relevancy

This helps answer questions that matter in production:

- Is the answer supported by the retrieved context?
- Did the retrieval stage bring back too much noise?
- Did the system miss important information?
- Does the answer actually address the question asked?

That turns quality into something observable and testable.

### 5. Drift monitoring

A strong AI system should not only work when it is first built. It should also help operators understand whether it is changing over time.

DocIntel includes drift reporting with Evidently so it can track changes in:

- query characteristics
- embedding behavior
- retrieval patterns
- report-level status over time

This gives the system an operational memory. Instead of waiting for complaints, an operator can inspect drift reports and identify degradation trends earlier.

### 6. Operations dashboard

The Streamlit dashboard is the user interface for the people operating the system rather than the people building it.

It includes pages for:

- evaluation trends
- drift reports
- cost and latency
- retrieval exploration

This is important because a production-grade AI system should be inspectable by non-developer stakeholders, not only by whoever can read logs or query the database manually.

* * *

## Core Intelligence Engines

### Hybrid retrieval engine

This is the search heart of the system.

It combines:

- BM25 for exact language matching
- pgvector for semantic recall
- Reciprocal Rank Fusion for robust combination
- cross-encoder reranking for final precision

This design avoids the usual weakness of vector-only RAG, where semantically similar but legally imprecise passages can outrank the exact article the user actually needs.

### Citation grounding engine

This engine makes the output trustworthy.

Rather than returning only generated text, it extracts and resolves citation references so every answer can be tied back to evidence inside the corpus.

That moves the project away from "model-generated explanation" and toward "traceable document intelligence."

### Evaluation engine

This engine makes quality measurable.

The RAGAS harness allows the repo to score the system on multiple dimensions instead of relying on intuition or spot checks.

That matters because retrieval quality and answer grounding are often the first things to degrade when teams modify prompts, models, or ranking logic.

### Observability engine

This engine makes the system inspectable.

LangSmith traces, Prometheus-style metrics, request IDs, latency tracking, token accounting, and structured logs all make it possible to understand what happened during retrieval and generation.

### Drift engine

This engine makes the system durable over time.

Using Evidently, the platform produces drift reports that help answer a simple but important operational question:

"Is the system still behaving like the system we originally validated?"

### Operations dashboard

This is the human-facing control surface for the intelligence engines above.

It turns raw technical signals into something that a product owner, AI lead, or operator can actually use.

* * *

## Quality Validation

### Verified corpus

The repository uses the official EU AI Act PDF as its working corpus.

Verified corpus snapshot:

- 144 pages
- 331 indexed chunks
- structure-aware chunking with page and section metadata

### Retrieval benchmark

The retrieval benchmark demonstrates why the hybrid design matters.

| Strategy | Precision@10 | Recall@10 |
|---|---:|---:|
| `vector_only` | 0.100 | 0.500 |
| `bm25_only` | 0.150 | 0.750 |
| `hybrid` | 0.150 | 0.750 |
| `hybrid_reranked` | 0.150 | 0.750 |

This is not about claiming perfect retrieval. It is about showing that the system architecture produces materially stronger search behavior than a weaker baseline.

### Automated quality checks

The repository includes:

- linting
- type checking
- backend tests
- dashboard tests
- container build verification in CI

This matters because production-minded AI systems should be engineered with the same discipline expected from non-AI systems.

### Operational validation

The project also validates:

- metrics exposure
- retrieval traces
- drift report generation
- dashboard rendering
- containerized builds

So quality here is not only "the model answered." It is "the whole system is behaving coherently."

* * *

## Detailed Deployment Guide

The system can be run either as a local development stack or as a production-shaped Docker deployment.

### Prerequisites

| Requirement | Version | Purpose |
|---|---|---|
| Python | 3.12+ | API and data pipeline runtime |
| Docker Desktop | Current | Local orchestration and database runtime |
| PostgreSQL | 16 | Primary database |
| uv | Current | Dependency management |

### Environment setup

```powershell
Copy-Item .env.example .env
```

Key environment values include:

- `DATABASE_URL`
- `API_KEYS`
- `SECRET_KEY`
- `OPENROUTER_API_KEY`
- `DEFAULT_GENERATION_MODEL`
- `DEFAULT_JUDGE_MODEL`
- `LANGSMITH_API_KEY`
- `LANGSMITH_TRACING`

### Local development

```powershell
docker compose up -d db
uv run --directory apps/api alembic upgrade head
uv run --directory apps/api uvicorn docintel.main:app --reload --app-dir src
uv run --directory apps/dashboard streamlit run app.py
```

This gives you:

- FastAPI API surface
- PostgreSQL plus pgvector
- Streamlit operations dashboard

### Production-shaped deployment

```powershell
docker compose -f docker-compose.yml -f docker-compose.prod.yml config
docker compose -f docker-compose.yml -f ops/docker/compose.full.yml up -d
```

This repository includes:

- base Compose stack
- production-shaped overlay
- dashboard overlay
- API Dockerfile
- dashboard Dockerfile

### Verification commands

```powershell
uvx --from ruff==0.15.7 ruff check apps/api/src apps/api/tests apps/dashboard
uv run --directory apps/api --with mypy==1.18.2 mypy --config-file ../../mypy.ini src
uv run --directory apps/api pytest tests -v
uv run --directory apps/dashboard pytest tests/test_db_queries.py -v
uv run --directory apps/api python -m docintel.tools.benchmark_retrieval --top-k 10
uv run --directory apps/api python -m docintel.tools.run_drift --window-days 7 --reference-window-days 7
```

* * *

## Development Notes

### Repository structure

```text
apps/
  api/                         FastAPI control plane
    src/docintel/
      models/                  SQLAlchemy models
      routers/                 API endpoints
      services/
        ingestion/             PDF parsing, chunking, embeddings
        retrieval/             BM25, vector, fusion, reranking
        generation/            prompts, citations, LLM client
        evaluation/            RAGAS harness and CI gate
        monitoring/            tracing and metrics
        drift/                 Evidently reports and scheduler
      tools/                   benchmark, eval, ingest, drift runners
  dashboard/                   Streamlit operations dashboard
fixtures/                      evaluation fixture and schema
ops/docker/                    Compose overlays and pgvector setup
```

### Public API surface

- `POST /api/v1/documents`
- `GET /api/v1/documents`
- `GET /api/v1/documents/{id}`
- `POST /api/v1/search`
- `POST /api/v1/answer`
- `POST /api/v1/eval/runs`
- `GET /api/v1/eval/runs`
- `GET /api/v1/drift/reports`
- `GET /api/v1/health/liveness`
- `GET /api/v1/health/readiness`
- `GET /metrics`

### Technical stack

- FastAPI
- PostgreSQL 16
- pgvector
- SQLAlchemy
- Alembic
- sentence-transformers
- RAGAS
- LangSmith
- Evidently
- Streamlit
- Docker
- GitHub Actions

### What this project is designed to show technically

- backend API design
- retrieval system engineering
- production-minded LLM integration
- evaluation-driven AI workflows
- observability and monitoring
- dashboard-driven AI operations
- containerized deployment

* * *

## References

- EU AI Act official text
- FastAPI
- PostgreSQL
- pgvector
- sentence-transformers
- RAGAS
- LangSmith
- Evidently
- Streamlit

* * *

## License

MIT

* * *

## Author

**Mehul Upase**

- GitHub: [@Mehulupase01](https://github.com/Mehulupase01)
- Email: `siya.mehul@outlook.com`
