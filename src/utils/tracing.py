"""Langfuse tracing utilities."""

from contextvars import ContextVar
from typing import Optional

from langfuse import Langfuse
from langfuse.types import TraceContext

from ..core.config import get_settings
from .logger import get_logger

logger = get_logger()

_langfuse_client: Langfuse | None = None
_current_trace_context: ContextVar[Optional[TraceContext]] = ContextVar(
    "langfuse_trace_context", default=None
)
_current_root_span: ContextVar[Optional[object]] = ContextVar(
    "langfuse_root_span", default=None
)


def _has_keys() -> bool:
    settings = get_settings()
    return bool(settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY)


def get_langfuse() -> Langfuse | None:
    """Get or create Langfuse client if configured."""
    global _langfuse_client
    if not _has_keys():
        return None
    if _langfuse_client is None:
        settings = get_settings()
        host = settings.LANGFUSE_BASE_URL or settings.LANGFUSE_HOST
        _langfuse_client = Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY.get_secret_value(),
            secret_key=settings.LANGFUSE_SECRET_KEY.get_secret_value(),
            host=host,
        )
        logger.info("langfuse_initialized", host=host)
    return _langfuse_client


def start_trace(
    name: str,
    input: Optional[dict] = None,
    metadata: Optional[dict] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    tags: Optional[list[str]] = None,
):
    """Start a Langfuse trace if configured.

    Langfuse SDK v2 uses trace_context + spans. We create a root span as the trace.
    """
    client = get_langfuse()
    if client is None:
        return None

    trace_id = client.create_trace_id()
    trace_context: TraceContext = {"trace_id": trace_id}
    _current_trace_context.set(trace_context)

    try:
        client.update_current_trace(
            name=name,
            input=input,
            metadata=metadata,
            user_id=user_id,
            session_id=session_id,
            tags=tags,
        )
    except Exception as exc:  # pragma: no cover
        logger.warning("langfuse_update_trace_failed", error=str(exc))

    try:
        root_span = client.start_span(
            name=name,
            trace_context=trace_context,
            input=input,
            metadata=metadata,
        )
        _current_root_span.set(root_span)
        return root_span
    except Exception as exc:  # pragma: no cover
        logger.warning("langfuse_start_root_span_failed", error=str(exc))
        return None


def get_trace_context() -> Optional[TraceContext]:
    """Get active trace context from context, if any."""
    return _current_trace_context.get()


def get_root_span():
    """Get root span for the current trace."""
    return _current_root_span.get()


def end_trace(root_span, output: Optional[dict] = None, metadata: Optional[dict] = None):
    """End a trace safely (end root span)."""
    if root_span is None:
        return
    try:
        # Update with output/metadata before ending (Langfuse v3 API)
        if output is not None or metadata is not None:
            root_span.update(output=output, metadata=metadata)
        root_span.end()
    except Exception as exc:  # pragma: no cover - tracing shouldn't break app
        logger.warning("langfuse_end_trace_failed", error=str(exc))
    finally:
        _current_trace_context.set(None)
        _current_root_span.set(None)


def start_span(name: str, input: Optional[dict] = None, metadata: Optional[dict] = None):
    """Start a span attached to the current trace."""
    client = get_langfuse()
    trace_context = get_trace_context()
    root_span = get_root_span()
    if client is None or trace_context is None:
        return None
    try:
        span_context: TraceContext = dict(trace_context)
        if root_span is not None:
            span_context["parent_span_id"] = root_span.id
        return client.start_span(
            name=name,
            trace_context=span_context,
            input=input,
            metadata=metadata,
        )
    except Exception as exc:  # pragma: no cover
        logger.warning("langfuse_start_span_failed", error=str(exc))
        return None


def end_span(
    span,
    output: Optional[dict] = None,
    metadata: Optional[dict] = None,
    status: Optional[str] = None,
):
    """End a span safely."""
    if span is None:
        return
    try:
        # Update with output/metadata/status before ending (Langfuse v3 API)
        if output is not None or metadata is not None or status is not None:
            span.update(output=output, metadata=metadata, status_message=status)
        span.end()
    except Exception as exc:  # pragma: no cover
        logger.warning("langfuse_end_span_failed", error=str(exc))


def flush_langfuse():
    """Flush pending traces to Langfuse.
    
    This ensures all traces in the queue are sent to the Langfuse server.
    Critical for development environments where traces might be lost on shutdown.
    """
    client = get_langfuse()
    if client is not None:
        try:
            logger.info("flushing_langfuse_traces")
            client.flush()
            logger.info("langfuse_traces_flushed")
        except Exception as exc:  # pragma: no cover
            logger.warning("langfuse_flush_failed", error=str(exc))
