from __future__ import annotations

import argparse
import asyncio
import hashlib
import uuid
from dataclasses import dataclass, replace
from statistics import mean
from unittest.mock import patch

from sqlalchemy import delete, select

from docintel.database import get_session_factory
from docintel.models.chunk import EMBEDDING_DIM, Chunk
from docintel.models.document import Document, DocumentStatus
from docintel.models.query import Query, RetrievalStrategy
from docintel.services.retrieval.hybrid import hybrid_search


BENCHMARK_SOURCE_URI = "benchmark://phase3-retrieval-fixture"


@dataclass(frozen=True, slots=True)
class BenchmarkCase:
    query: str
    expected_ordinals: frozenset[int]
    vector_dimension: int
    rerank_phrases: tuple[str, ...]


BENCHMARK_CASES = (
    BenchmarkCase(
        query="What is a high-risk AI system?",
        expected_ordinals=frozenset({0, 1}),
        vector_dimension=0,
        rerank_phrases=("high-risk ai system", "annex iii", "article 6"),
    ),
    BenchmarkCase(
        query="What are prohibited AI practices?",
        expected_ordinals=frozenset({11, 12}),
        vector_dimension=1,
        rerank_phrases=("prohibited ai practices", "article 5", "social scoring"),
    ),
    BenchmarkCase(
        query="What must the EU declaration of conformity contain?",
        expected_ordinals=frozenset({22, 23}),
        vector_dimension=2,
        rerank_phrases=("eu declaration of conformity", "annex v", "statement of compliance"),
    ),
    BenchmarkCase(
        query="What information is submitted when registering high-risk AI systems?",
        expected_ordinals=frozenset({33, 34}),
        vector_dimension=3,
        rerank_phrases=("registering high-risk ai systems", "registration of high-risk ai systems", "annex viii"),
    ),
)

BENCHMARK_CASES_BY_QUERY = {case.query.lower(): case for case in BENCHMARK_CASES}


class _BenchmarkEmbedder:
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            case = BENCHMARK_CASES_BY_QUERY.get(text.lower())
            if case is None:
                raise ValueError(f"Unsupported benchmark query: {text}")
            vectors.append(_query_embedding(case.vector_dimension))
        return vectors


class _BenchmarkReranker:
    def rerank(self, query: str, candidates):
        case = BENCHMARK_CASES_BY_QUERY.get(query.lower())
        if case is None:
            raise ValueError(f"Unsupported benchmark query: {query}")

        reranked = []
        for candidate in candidates:
            haystack = f"{candidate.section_path or ''}\n{candidate.text}".lower()
            score = sum(1.0 for phrase in case.rerank_phrases if phrase in haystack)
            score += 0.001 * max(0, 100 - (candidate.rank or 100))
            reranked.append(replace(candidate, rerank_score=score))

        reranked.sort(key=lambda item: item.rerank_score or 0.0, reverse=True)
        return [replace(item, rank=rank) for rank, item in enumerate(reranked, start=1)]


async def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark DocIntel retrieval strategies on a seeded fixture.")
    parser.add_argument("--top-k", type=int, default=10)
    args = parser.parse_args()

    session_factory = get_session_factory()
    async with session_factory() as session:
        document = await _seed_benchmark_fixture(session)
        benchmark_query_ids: list[uuid.UUID] = []
        try:
            with (
                patch("docintel.services.retrieval.hybrid.get_embedder", lambda: _BenchmarkEmbedder()),
                patch("docintel.services.retrieval.hybrid.get_reranker", lambda: _BenchmarkReranker()),
            ):
                scores: dict[str, dict[str, float]] = {}
                for strategy in RetrievalStrategy:
                    precision_values: list[float] = []
                    recall_values: list[float] = []
                    for case in BENCHMARK_CASES:
                        result = await hybrid_search(
                            session=session,
                            query=case.query,
                            strategy=strategy,
                            top_k=args.top_k,
                            rerank_top_n=max(args.top_k, 10),
                            rrf_k=60,
                            document_ids=[document.id],
                        )
                        benchmark_query_ids.append(result.query_id)
                        relevant_count = sum(1 for item in result.results if item.ordinal in case.expected_ordinals)
                        precision_values.append(relevant_count / max(args.top_k, 1))
                        recall_values.append(relevant_count / len(case.expected_ordinals))

                    scores[strategy.value] = {
                        "precision_at_k": mean(precision_values),
                        "recall_at_k": mean(recall_values),
                    }
        finally:
            await _cleanup_benchmark_data(session, document.id, benchmark_query_ids)

    print("strategy\tprecision@k\trecall@k")
    for strategy, metrics in scores.items():
        print(f"{strategy}\t{metrics['precision_at_k']:.3f}\t{metrics['recall_at_k']:.3f}")


async def _seed_benchmark_fixture(session) -> Document:
    existing = await session.scalar(select(Document).where(Document.source_uri == BENCHMARK_SOURCE_URI))
    if existing is not None:
        await session.delete(existing)
        await session.flush()

    document = Document(
        title="Phase 3 Retrieval Benchmark Fixture",
        source_uri=BENCHMARK_SOURCE_URI,
        sha256=hashlib.sha256(BENCHMARK_SOURCE_URI.encode("utf-8")).hexdigest(),
        page_count=8,
        byte_size=0,
        status=DocumentStatus.READY,
        metadata_json={"benchmark_fixture": True},
    )
    session.add(document)
    await session.flush()

    cursor = 0
    chunks: list[Chunk] = []
    for ordinal, (section_path, text, embedding) in enumerate(_benchmark_fixture_rows()):
        text_length = len(text)
        chunks.append(
            Chunk(
                document_id=document.id,
                ordinal=ordinal,
                text=text,
                token_count=max(len(text.split()), 1),
                char_start=cursor,
                char_end=cursor + text_length,
                page_start=(ordinal // 6) + 1,
                page_end=(ordinal // 6) + 1,
                section_path=section_path,
                embedding=embedding,
                metadata_json={"benchmark_fixture": True},
            )
        )
        cursor += text_length + 1

    session.add_all(chunks)
    await session.commit()
    return document


async def _cleanup_benchmark_data(session, document_id: uuid.UUID, query_ids: list[uuid.UUID]) -> None:
    if query_ids:
        await session.execute(delete(Query).where(Query.id.in_(query_ids)))

    document = await session.scalar(select(Document).where(Document.id == document_id))
    if document is not None:
        await session.delete(document)

    await session.commit()


def _benchmark_fixture_rows() -> list[tuple[str, str, list[float]]]:
    rows: list[tuple[str, str, list[float]]] = []
    rows.extend(_theme_rows(
        theme_dim=0,
        fallback_dim=100,
        relevant_rows=[
            (
                "Article 6",
                "Article 6 defines a high-risk AI system by reference to Annex III and product safety legislation.",
                _primary_embedding(0),
            ),
            (
                "Annex III",
                "Annex III lists use cases that classify a high-risk AI system, including employment and biometric scenarios.",
                _support_embedding(0, 100),
            ),
        ],
        distractor_rows=[
            ("Title III", "Providers of regulated applications must retain technical logs for later audit review."),
            ("Title III", "Human oversight measures guide operators of regulated applications during deployment."),
            ("Title III", "Accuracy, robustness, and cybersecurity controls apply to regulated applications."),
            ("Title III", "Post-market monitoring plans track incidents involving regulated applications."),
            ("Title III", "Risk management files document hazards for regulated applications before release."),
            ("Title III", "Instructions for use explain operating limits for regulated applications."),
            ("Title III", "Conformity assessment evidence must be retained for regulated applications."),
            ("Title III", "Deployers must assign trained operators to regulated applications."),
            ("Title III", "Serious incident reporting timelines apply to regulated applications."),
        ],
    ))
    rows.extend(_theme_rows(
        theme_dim=1,
        fallback_dim=101,
        relevant_rows=[
            (
                "Article 5",
                "Article 5 sets out prohibited AI practices, including manipulative and exploitative uses.",
                _primary_embedding(1),
            ),
            (
                "Article 5",
                "The prohibited AI practices ban covers social scoring and certain real-time remote biometric identification uses.",
                _support_embedding(1, 101),
            ),
        ],
        distractor_rows=[
            ("Recitals", "Unacceptable use restrictions address manipulative design in sensitive settings."),
            ("Recitals", "Restricted surveillance uses require narrow safeguards and public authority control."),
            ("Recitals", "Certain exploitative design patterns trigger strict oversight duties."),
            ("Recitals", "Biometric surveillance exceptions are narrowly framed for public safety incidents."),
            ("Recitals", "Social influence tactics in vulnerable settings face severe regulatory scrutiny."),
            ("Recitals", "Law-enforcement deployments need tightly defined legal bases and safeguards."),
            ("Recitals", "Remote identification deployments require exceptional public-interest justification."),
            ("Recitals", "Emotion inference deployments in workplaces face stringent restrictions."),
            ("Recitals", "Manipulative interface design in essential services draws heightened scrutiny."),
        ],
    ))
    rows.extend(_theme_rows(
        theme_dim=2,
        fallback_dim=102,
        relevant_rows=[
            (
                "Annex V",
                "Annex V specifies what the EU declaration of conformity must contain for high-risk AI systems.",
                _primary_embedding(2),
            ),
            (
                "Annex V",
                "The EU declaration of conformity includes provider identity, system identification, and the statement of compliance in Annex V.",
                _support_embedding(2, 102),
            ),
        ],
        distractor_rows=[
            ("Annex IV", "The technical documentation file records design choices, validation, and testing evidence."),
            ("Annex IV", "Providers keep architecture details and dataset summaries in the technical file."),
            ("Annex IV", "Instructions for use explain deployment assumptions and residual operational limits."),
            ("Annex IV", "The technical file identifies post-market monitoring arrangements and incident pathways."),
            ("Annex IV", "Risk control evidence and validation summaries remain in the technical file."),
            ("Annex IV", "The technical file includes contact details for the responsible provider representative."),
            ("Annex IV", "System identification labels appear across the technical file and instructions for use."),
            ("Annex IV", "Providers store testing summaries and quality-management references in the technical file."),
            ("Annex IV", "The technical file supports conformity assessment bodies during pre-market review."),
        ],
    ))
    rows.extend(_theme_rows(
        theme_dim=3,
        fallback_dim=103,
        relevant_rows=[
            (
                "Annex VIII",
                "Annex VIII lists the information submitted when registering high-risk AI systems in the EU database.",
                _primary_embedding(3),
            ),
            (
                "Annex VIII",
                "Registration of high-risk AI systems requires provider details, system identification, and conformity references under Annex VIII.",
                _support_embedding(3, 103),
            ),
        ],
        distractor_rows=[
            ("Title VIII", "Post-market monitoring records capture incidents and corrective action planning."),
            ("Title VIII", "Providers keep logged records available for supervisory investigations."),
            ("Title VIII", "Serious incident notices include timelines, impact summaries, and mitigation steps."),
            ("Title VIII", "Corrective actions are tracked until the supervisory authority closes the case."),
            ("Title VIII", "Providers retain contact details for market surveillance cooperation duties."),
            ("Title VIII", "Operational logs support audits and post-market review of deployed systems."),
            ("Title VIII", "Supervisory coordination relies on traceable identifiers and incident references."),
            ("Title VIII", "Providers document the last conformity assessment route used before release."),
            ("Title VIII", "Oversight teams retain references needed for follow-up investigations."),
        ],
    ))
    return rows


def _theme_rows(
    theme_dim: int,
    fallback_dim: int,
    relevant_rows: list[tuple[str, str, list[float]]],
    distractor_rows: list[tuple[str, str]],
) -> list[tuple[str, str, list[float]]]:
    rows = list(relevant_rows)
    for index, (section_path, text) in enumerate(distractor_rows, start=1):
        rows.append((section_path, text, _distractor_embedding(theme_dim, fallback_dim + index)))
    return rows


def _query_embedding(theme_dim: int) -> list[float]:
    vector = [0.0] * EMBEDDING_DIM
    vector[theme_dim] = 1.0
    return vector


def _primary_embedding(theme_dim: int) -> list[float]:
    vector = [0.0] * EMBEDDING_DIM
    vector[theme_dim] = 1.0
    return vector


def _support_embedding(theme_dim: int, fallback_dim: int) -> list[float]:
    vector = [0.0] * EMBEDDING_DIM
    vector[theme_dim] = 0.12
    vector[fallback_dim] = 1.0
    return vector


def _distractor_embedding(theme_dim: int, secondary_dim: int) -> list[float]:
    vector = [0.0] * EMBEDDING_DIM
    vector[theme_dim] = 0.9
    vector[secondary_dim] = 0.2
    return vector


if __name__ == "__main__":
    asyncio.run(main())
