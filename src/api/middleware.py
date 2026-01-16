"""FastAPI middleware for logging, error handling, and CORS."""

import time
import uuid
from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..core.config import get_settings
from ..core.exceptions import RAGException
from ..utils.logger import get_logger

logger = get_logger()


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add request ID to all requests."""

    async def dispatch(self, request: Request, call_next):
        """Add request ID and log request."""
        request_id = str(uuid.uuid4())
        request.state.id = request_id

        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time

        logger.info(
            "request_completed",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration * 1000, 2),
        )

        response.headers["X-Request-ID"] = request_id
        return response


def setup_cors(app):
    """Setup CORS middleware."""
    settings = get_settings()
    origins = (
        settings.ALLOWED_ORIGINS.split(",")
        if settings.ALLOWED_ORIGINS != "*"
        else ["*"]
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )


async def exception_handler(request: Request, exc: RAGException):
    """Handle RAG exceptions."""
    logger.error(
        "rag_exception",
        request_id=getattr(request.state, "id", "unknown"),
        error_type=type(exc).__name__,
        error_message=str(exc),
    )
    return JSONResponse(
        status_code=500,
        content={"error": "Service error", "request_id": getattr(request.state, "id", "unknown")},
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """Handle generic exceptions."""
    logger.exception(
        "unhandled_exception",
        request_id=getattr(request.state, "id", "unknown"),
        error_type=type(exc).__name__,
    )
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"},
    )
