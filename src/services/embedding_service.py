"""Embedding service using sentence-transformers."""

import asyncio
from typing import List
from sentence_transformers import SentenceTransformer

from ..core.config import get_settings
from ..core.exceptions import ConfigurationException


class EmbeddingService:
    """Singleton service for generating embeddings."""

    _instance: "EmbeddingService | None" = None
    _model: SentenceTransformer | None = None

    def __init__(self):
        """Initialize embedding service."""
        if EmbeddingService._instance is not None:
            raise RuntimeError("Use get_embedding_service() instead")
        self._initialized = False

    async def initialize(self) -> None:
        """Load the embedding model (async)."""
        if self._initialized:
            return

        settings = get_settings()
        try:
            # Load model in thread pool (CPU-bound)
            loop = asyncio.get_event_loop()
            EmbeddingService._model = await loop.run_in_executor(
                None, SentenceTransformer, settings.EMBEDDING_MODEL
            )
            self._initialized = True
        except Exception as e:
            raise ConfigurationException(f"Failed to load embedding model: {e}")

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts."""
        if not self._initialized:
            await self.initialize()

        if EmbeddingService._model is None:
            raise ConfigurationException("Embedding model not loaded")

        # Run CPU-bound encoding in thread pool
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None, EmbeddingService._model.encode, texts
        )
        return embeddings.tolist()

    async def embed_single(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        embeddings = await self.embed([text])
        return embeddings[0]


_embedding_service: EmbeddingService | None = None


async def get_embedding_service() -> EmbeddingService:
    """Get or create embedding service singleton."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
        await _embedding_service.initialize()
    return _embedding_service
