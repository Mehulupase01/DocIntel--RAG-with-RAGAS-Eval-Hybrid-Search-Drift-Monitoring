from __future__ import annotations

import numpy as np

from docintel.services.ingestion.embedder import get_embedder


def test_embedder():
    embeddings = get_embedder().embed_texts(
        ["The AI Act regulates high-risk systems.", "Providers must maintain technical documentation."]
    )

    assert len(embeddings) == 2
    assert len(embeddings[0]) == 384
    assert np.isclose(np.linalg.norm(embeddings[0]), 1.0, atol=1e-3)
    assert np.isclose(np.linalg.norm(embeddings[1]), 1.0, atol=1e-3)
