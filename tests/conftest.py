"""Pytest configuration and fixtures."""

from contextlib import asynccontextmanager

import pytest
from fastapi.testclient import TestClient

from src.main import app as base_app
from src.utils import metrics as metrics_module


@asynccontextmanager
async def _no_lifespan(_app):
    """Disable application startup side effects during tests."""
    yield


@pytest.fixture(scope="session")
def app():
    """Return FastAPI app with lifespan disabled."""
    base_app.router.lifespan_context = _no_lifespan
    return base_app


@pytest.fixture()
def client(app):
    """Provide a FastAPI test client."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def reset_metrics():
    """Reset metrics between tests for deterministic assertions."""
    metrics_module._metrics = metrics_module.Metrics()
    yield
