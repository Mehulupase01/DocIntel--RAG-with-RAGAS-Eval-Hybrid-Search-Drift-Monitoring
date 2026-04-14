from __future__ import annotations

from functools import lru_cache
from typing import Sequence

from sentence_transformers import SentenceTransformer

from docintel.config import get_settings


class Embedder:
    def __init__(self, model_name: str | None = None, cache_dir: str | None = None) -> None:
        settings = get_settings()
        self.model_name = model_name or settings.embedding_model
        self.cache_dir = cache_dir or settings.model_cache_dir
        self._model: SentenceTransformer | None = None

    def embed_texts(self, texts: Sequence[str], batch_size: int = 16) -> list[list[float]]:
        if not texts:
            return []

        embeddings = self._get_model().encode(
            list(texts),
            batch_size=batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return embeddings.tolist()

    def _get_model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(self.model_name, cache_folder=self.cache_dir, device="cpu")
        return self._model


@lru_cache
def get_embedder() -> Embedder:
    return Embedder()
