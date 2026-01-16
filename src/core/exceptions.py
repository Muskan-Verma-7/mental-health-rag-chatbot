"""Custom exception hierarchy for RAG system."""


class RAGException(Exception):
    """Base exception for all RAG errors."""

    pass


class SafetyException(RAGException):
    """High-risk content detected."""

    def __init__(self, message: str, risk_level: str = "high"):
        super().__init__(message)
        self.risk_level = risk_level


class RetrievalException(RAGException):
    """Vector search or retrieval failed."""

    pass


class LLMException(RAGException):
    """LLM generation failed."""

    pass


class ConfigurationException(RAGException):
    """Invalid or missing configuration."""

    pass
