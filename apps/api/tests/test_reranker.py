from __future__ import annotations

import uuid

from docintel.services.retrieval.fusion import ChunkScore
from docintel.services.retrieval.reranker import Reranker


class _StubCrossEncoder:
    def __init__(self, scores):
        self._scores = scores

    def predict(self, _pairs):
        return self._scores


def test_reranker():
    reranker = Reranker(model=_StubCrossEncoder([0.1, 0.9, 0.3]))
    candidates = [
        ChunkScore(chunk_id=uuid.UUID(int=1), document_id=uuid.UUID(int=11), document_title="Doc", ordinal=0, text="alpha", section_path=None, page_start=1, page_end=1),
        ChunkScore(chunk_id=uuid.UUID(int=2), document_id=uuid.UUID(int=12), document_title="Doc", ordinal=1, text="beta", section_path=None, page_start=1, page_end=1),
        ChunkScore(chunk_id=uuid.UUID(int=3), document_id=uuid.UUID(int=13), document_title="Doc", ordinal=2, text="gamma", section_path=None, page_start=1, page_end=1),
    ]

    reranked = reranker.rerank("query", candidates)

    assert [item.chunk_id for item in reranked] == [uuid.UUID(int=2), uuid.UUID(int=3), uuid.UUID(int=1)]
    assert reranked[0].rerank_score == 0.9
