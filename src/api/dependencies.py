"""FastAPI dependencies and lifespan management."""

from contextlib import asynccontextmanager
from fastapi import FastAPI

from ..services.embedding_service import get_embedding_service
from ..core.config import get_settings
from ..core.database import get_database
from ..utils.logger import get_logger

logger = get_logger()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan (startup/shutdown)."""
    # Startup
    logger.info("application_starting")
    try:
        # Warm up embedding model (optional for low-memory environments)
        if settings.EMBEDDING_PROVIDER == "local":
            if settings.EMBEDDING_WARMUP:
                await get_embedding_service()
                logger.info("embedding_service_ready")
            else:
                logger.info("embedding_warmup_skipped")
        else:
            # Initialize Azure client to fail fast on config issues
            await get_embedding_service()
            logger.info("azure_embedding_service_ready")

        # Initialize database
        db = get_database()
        await db.setup_schema()
        logger.info("database_ready")

        logger.info("application_started")
    except Exception as e:
        logger.error("startup_failed", error=str(e))
        raise

    yield

    # Shutdown
    logger.info("application_shutting_down")
    
    # Flush Langfuse traces before shutdown
    from ..utils.tracing import flush_langfuse
    flush_langfuse()
    
    # Cleanup resources if needed
    logger.info("application_stopped")
