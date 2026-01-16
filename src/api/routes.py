"""API route handlers."""

import time
import uuid
from fastapi import APIRouter, Request, HTTPException
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .models import ChatRequest, ChatResponse, HealthResponse, MetricsResponse
from ..services.safety_service import get_safety_service
from ..services.retrieval_service import get_retrieval_service
from ..services.llm_service import get_llm_service
from ..core.config import get_settings
from ..core.exceptions import SafetyException
from ..utils.logger import get_logger
from ..utils.tracing import start_trace, end_trace, start_span, end_span, flush_langfuse
from ..utils.metrics import get_metrics

logger = get_logger()
router = APIRouter()

# Rate limiting
limiter = Limiter(key_func=get_remote_address)


@router.post("/chat", response_model=ChatResponse)
@limiter.limit("10/minute")
async def chat(request: Request, body: ChatRequest) -> ChatResponse:
    """Main chat endpoint for mental health support."""
    request_id = getattr(request.state, "id", str(uuid.uuid4()))
    start_time = time.time()
    

    trace = start_trace(
        name="chat_request",
        input={"message": body.message},
        metadata={"request_id": request_id, "path": "/chat"},
        user_id=str(request.client.host) if request.client else None,
    )

    try:
        # Safety check
        safety_service = get_safety_service()
        sanitized_message = safety_service.sanitize_input(body.message)
        safety_span = start_span(
            "safety_check",
            input={"message": sanitized_message},
        )
        safety_result = safety_service.check(sanitized_message)
        end_span(
            safety_span,
            output={
                "risk_level": safety_result.risk_level,
                "action": safety_result.action,
            },
        )
        

        if safety_result.risk_level == "high":
            metrics = get_metrics()
            metrics.record_request(time.time() - start_time, safety_blocked=True)
            response = ChatResponse(
                response=safety_result.message or "Please contact a crisis helpline.",
                safety_status="blocked",
                latency_ms=round((time.time() - start_time) * 1000, 2),
                sources_used=0,
                request_id=request_id,
            )
            end_trace(
                trace,
                output={
                    "safety_status": "blocked",
                    "sources_used": 0,
                    "latency_ms": response.latency_ms,
                },
            )
            flush_langfuse()
            return response

        # Retrieve relevant documents
        
        retrieval_span = start_span(
            "retrieval",
            input={"query": sanitized_message},
        )
        retrieval_service = get_retrieval_service()
        documents = await retrieval_service.retrieve(sanitized_message)
        end_span(
            retrieval_span,
            output={
                "documents_found": len(documents),
                "topics": [doc.metadata.get("topic") for doc in documents],
                "scores": [round(doc.score, 3) for doc in documents],
            },
        )
        

        if not documents:
            response = ChatResponse(
                response="I understand you're going through a difficult time. While I don't have specific resources for this right now, please consider speaking with a mental health professional who can provide personalized support.",
                safety_status="pass",
                latency_ms=round((time.time() - start_time) * 1000, 2),
                sources_used=0,
                request_id=request_id,
            )
            end_trace(
                trace,
                output={
                    "safety_status": "pass",
                    "sources_used": 0,
                    "latency_ms": response.latency_ms,
                },
            )
            flush_langfuse()
            return response

        # Generate response
        llm_service = get_llm_service()
        context = [doc.content for doc in documents]
        llm_span = start_span(
            "llm_generate",
            input={"model": llm_service.model, "context_chunks": len(context)},
        )
        response_text = await llm_service.generate(
            sanitized_message,
            context,
            history=body.conversation_history,
        )
        end_span(llm_span, output={"response_length": len(response_text)})

        latency_ms = round((time.time() - start_time) * 1000, 2)

        # Record metrics
        metrics = get_metrics()
        metrics.record_request(
            time.time() - start_time,
            safety_blocked=(safety_result.risk_level != "low"),
        )

        response = ChatResponse(
            response=response_text,
            safety_status="warning" if safety_result.risk_level == "medium" else "pass",
            latency_ms=latency_ms,
            sources_used=len(documents),
            request_id=request_id,
        )
        end_trace(
            trace,
            output={
                "safety_status": response.safety_status,
                "sources_used": response.sources_used,
                "latency_ms": response.latency_ms,
            },
        )
        
        # Flush traces immediately for development
        flush_langfuse()
        
        return response

    except SafetyException as e:
        end_trace(trace, output={"error": str(e), "error_type": "SafetyException"})
        flush_langfuse()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("chat_error", request_id=request_id, error=str(e))
        end_trace(trace, output={"error": str(e), "error_type": "Exception"})
        flush_langfuse()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check endpoint."""
    settings = get_settings()
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        environment=settings.ENVIRONMENT,
    )


@router.get("/metrics", response_model=MetricsResponse)
async def metrics() -> MetricsResponse:
    """Metrics endpoint."""
    metrics_obj = get_metrics()
    return MetricsResponse(
        total_requests=metrics_obj.total_requests,
        avg_latency_ms=metrics_obj.avg_latency_ms,
        safety_blocks=metrics_obj.safety_blocks,
        uptime_seconds=metrics_obj.uptime_seconds,
    )
