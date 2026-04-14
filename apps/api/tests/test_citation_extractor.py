from __future__ import annotations

import uuid

from docintel.schemas.search import RetrievedChunk
from docintel.services.generation.citation_extractor import extract_citations


def _context(index: int) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        document_title="EU AI Act",
        ordinal=index,
        text=f"Context excerpt {index}",
        section_path=f"Article {index + 1}",
        page_start=index + 1,
        page_end=index + 1,
        rank=index + 1,
        bm25_score=0.8,
        vector_score=0.7,
        fused_score=0.9,
        rerank_score=0.95,
    )


def test_citation_extractor_parses_markers():
    contexts = [_context(0), _context(1)]

    answer, citations = extract_citations(
        "High-risk AI systems are defined in Article 6 [c#1] and listed in Annex III [c#2].",
        contexts,
    )

    assert answer == "High-risk AI systems are defined in Article 6 and listed in Annex III."
    assert [citation.ordinal for citation in citations] == [1, 2]
    assert [citation.context.chunk_id for citation in citations] == [contexts[0].chunk_id, contexts[1].chunk_id]


def test_citation_extractor_drops_unknown_markers():
    contexts = [_context(0)]

    answer, citations = extract_citations("This is grounded [c#3] in Article 6 [c#1].", contexts)

    assert answer == "This is grounded in Article 6."
    assert len(citations) == 1
    assert citations[0].ordinal == 1
    assert citations[0].context.chunk_id == contexts[0].chunk_id
