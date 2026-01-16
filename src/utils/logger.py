"""Structured logging configuration with structlog."""

import logging
import structlog
from ..core.config import get_settings


def configure_logging():
    """Configure structured logging."""
    settings = get_settings()

    # Convert string log level to logging constant
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger():
    """Get configured logger."""
    return structlog.get_logger()


# Configure on import
configure_logging()
