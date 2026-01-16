"""Integration tests for API endpoints."""

from dataclasses import dataclass

from src.services.retrieval_service import Document


@dataclass
class _DummySafetyResult:
    risk_level: str
    action: str
    message: str | None = None


class _DummySafetyService:
    def __init__(self, risk_level: str = "low", message: str | None = None):
        self._risk_level = risk_level
        self._message = message

    def sanitize_input(self, text: str) -> str:
        return text.strip()

    def check(self, _text: str) -> _DummySafetyResult:
        action = "block" if self._risk_level == "high" else "pass"
        return _DummySafetyResult(
            risk_level=self._risk_level, action=action, message=self._message
        )


class _DummyRetrievalService:
    def __init__(self, documents):
        self._documents = documents

    async def retrieve(self, _query: str):
        return self._documents


class _DummyLLMService:
    def __init__(self, response: str):
        self._response = response
        self.model = "test-model"

    async def generate(self, _query: str, _context, history=None):
        return self._response


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert "environment" in payload


def test_metrics_endpoint(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_requests"] == 0
    assert payload["safety_blocks"] == 0


def test_chat_blocked(monkeypatch, client):
    from src.api import routes

    def _safety_service():
        return _DummySafetyService(
            risk_level="high",
            message="Please contact a crisis helpline.",
        )

    monkeypatch.setattr(routes, "get_safety_service", _safety_service)
    monkeypatch.setattr(
        routes,
        "get_retrieval_service",
        lambda: _DummyRetrievalService([]),
    )
    monkeypatch.setattr(routes, "get_llm_service", lambda: _DummyLLMService("unused"))

    response = client.post("/chat", json={"message": "I want to hurt myself"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["safety_status"] == "blocked"
    assert payload["sources_used"] == 0


def test_chat_no_documents(monkeypatch, client):
    from src.api import routes

    monkeypatch.setattr(routes, "get_safety_service", lambda: _DummySafetyService())
    monkeypatch.setattr(
        routes,
        "get_retrieval_service",
        lambda: _DummyRetrievalService([]),
    )
    monkeypatch.setattr(routes, "get_llm_service", lambda: _DummyLLMService("unused"))

    response = client.post("/chat", json={"message": "I'm feeling stressed"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["sources_used"] == 0
    assert payload["safety_status"] == "pass"


def test_chat_success(monkeypatch, client):
    from src.api import routes

    documents = [
        Document(content="helpful content", metadata={"topic": "stress"}, score=0.5)
    ]
    monkeypatch.setattr(routes, "get_safety_service", lambda: _DummySafetyService())
    monkeypatch.setattr(
        routes,
        "get_retrieval_service",
        lambda: _DummyRetrievalService(documents),
    )
    monkeypatch.setattr(
        routes,
        "get_llm_service",
        lambda: _DummyLLMService("supportive response"),
    )

    response = client.post("/chat", json={"message": "I'm feeling stressed"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["response"] == "supportive response"
    assert payload["sources_used"] == 1
    assert payload["safety_status"] == "pass"
