"""FastAPI application entry point."""

from fastapi import FastAPI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .api.routes import router
from .api.middleware import RequestIDMiddleware, setup_cors, exception_handler, generic_exception_handler
from .api.dependencies import lifespan
from .core.config import get_settings
from .core.exceptions import RAGException
from .utils.logger import get_logger
from .utils.tracing import get_langfuse

# Initialize OpenTelemetry instrumentation
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

logger = get_logger()
settings = get_settings()

# Initialize Langfuse client early to register OTEL processors
langfuse_client = get_langfuse()
if langfuse_client:
    logger.info("langfuse_otel_ready", message="OpenTelemetry instrumentation enabled with Langfuse")

# Create FastAPI app
app = FastAPI(
    title="Aumio RAG Mental Health Chatbot",
    description="Production-ready RAG system for mental health support",
    version="1.0.0",
    lifespan=lifespan,
)

# Add middleware
app.add_middleware(RequestIDMiddleware)
setup_cors(app)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Exception handlers
app.add_exception_handler(RAGException, exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Include routers
app.include_router(router)

# Instrument FastAPI for automatic OpenTelemetry tracing
FastAPIInstrumentor.instrument_app(app)

# Instrument HTTPX for outgoing HTTP requests
HTTPXClientInstrumentor().instrument()

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Aumio RAG Mental Health Chatbot API",
        "version": "1.0.0",
        "docs": "/docs",
    }
