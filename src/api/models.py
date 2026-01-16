"""Pydantic models for API requests and responses."""

from pydantic import BaseModel, Field, field_validator
from typing import Literal, List, Dict, Any


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    message: str = Field(..., min_length=1, max_length=1000)
    conversation_history: List[Dict[str, Any]] = Field(
        default_factory=list, max_length=10
    )

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        """Validate and sanitize message."""
        return v.strip()


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""

    response: str
    safety_status: Literal["pass", "warning", "blocked"]
    latency_ms: float
    sources_used: int
    request_id: str


class HealthResponse(BaseModel):
    """Response model for health endpoint."""

    status: str
    version: str
    environment: str


class MetricsResponse(BaseModel):
    """Response model for metrics endpoint."""

    total_requests: int
    avg_latency_ms: float
    safety_blocks: int
    uptime_seconds: float
