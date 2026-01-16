"""Database layer for Supabase with pgvector support."""

from typing import Any, Iterable
from supabase import create_client, Client

from .config import get_settings
from .exceptions import ConfigurationException, RetrievalException


class Database:
    """Supabase database client with connection pooling."""

    def __init__(self):
        """Initialize Supabase client."""
        settings = get_settings()
        try:
            # Use default client options for compatibility across supabase versions
            self.client: Client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_KEY.get_secret_value(),
            )
        except Exception as e:
            raise ConfigurationException(f"Failed to initialize Supabase client: {e}")

    async def setup_schema(self) -> None:
        """Verify required schema exists in Supabase."""
        try:
            # Simple check to ensure table exists and is accessible
            self.client.table("therapy_chunks").select("id").limit(1).execute()
        except Exception as e:
            raise ConfigurationException(
                "Supabase schema not ready. Run the SQL schema setup first."
            ) from e

    async def search_similar(
        self, embedding: list[float], top_k: int, threshold: float
    ) -> list[dict[str, Any]]:
        """Search for similar chunks using pgvector."""
        try:
            response = self.client.rpc(
                "match_therapy_chunks",
                {
                    "query_embedding": embedding,
                    "match_threshold": threshold,
                    "match_count": top_k,
                },
            ).execute()
            
        except Exception as e:
            raise RetrievalException(f"Vector search failed: {e}") from e

        data = response.data or []
        results: list[dict[str, Any]] = []
        for row in data:
            results.append(
                {
                    "content": row.get("content"),
                    "metadata": row.get("metadata", {}),
                    "score": row.get("similarity", 0.0),
                }
            )
        
        return results

    async def insert_chunks(self, chunks: list[dict[str, Any]]) -> None:
        """Insert chunks into database."""
        if not chunks:
            return

        # Supabase has limits on batch size; keep it conservative
        batch_size = 100
        try:
            for batch in _chunked(chunks, batch_size):
                self.client.table("therapy_chunks").insert(batch).execute()
        except Exception as e:
            raise RetrievalException(f"Failed to insert chunks: {e}") from e


_db_instance: Database | None = None


def get_database() -> Database:
    """Get or create database singleton."""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance


def _chunked(items: list[dict[str, Any]], size: int) -> Iterable[list[dict[str, Any]]]:
    """Yield items in fixed-size batches."""
    for i in range(0, len(items), size):
        yield items[i : i + size]
