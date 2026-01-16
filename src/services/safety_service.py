"""Safety filtering service for high-risk content detection."""

import re
from typing import Literal
from dataclasses import dataclass

from ..core.exceptions import SafetyException


@dataclass
class SafetyResult:
    """Result of safety check."""

    risk_level: Literal["low", "medium", "high"]
    action: str
    message: str | None = None


class SafetyService:
    """Service for detecting and handling high-risk content."""

    # Crisis keywords patterns (case-insensitive)
    HIGH_RISK_PATTERNS = [
        r"\b(suicid(e|al)|kill myself|end my life|take my life)\b",
        r"\b(self.?harm|self.?injury|cutting|hurting myself)\b",
        r"\b(want to die|wish I was dead|better off dead)\b",
        r"\b(overdose|poison|hang|jump off)\b",
    ]

    MEDIUM_RISK_PATTERNS = [
        r"\b(hopeless|no point|nothing matters)\b",
        r"\b(can't go on|can't cope|giving up)\b",
    ]

    CRISIS_RESOURCES = {
        "DE": {
            "phone": "TelefonSeelsorge: 0800 111 0 111, 0800 111 0 222, or 116 123",
            "online": "Online chat: https://online.telefonseelsorge.de",
        },
        "US": {
            "988": "Suicide & Crisis Lifeline: 988",
            "text": "Text HOME to 741741 (Crisis Text Line)",
        },
        "general": {
            "988": "988 Suicide & Crisis Lifeline",
            "text": "Crisis Text Line: Text HOME to 741741",
        },
    }

    def check(self, text: str) -> SafetyResult:
        """Check text for safety risks."""
        text_lower = text.lower()

        # Check high-risk patterns
        for pattern in self.HIGH_RISK_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return SafetyResult(
                    risk_level="high",
                    action="block",
                    message=self._get_crisis_message(),
                )

        # Check medium-risk patterns
        for pattern in self.MEDIUM_RISK_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return SafetyResult(
                    risk_level="medium",
                    action="warning",
                    message="If you're having thoughts of self-harm, please reach out to a mental health professional or crisis helpline.",
                )

        return SafetyResult(risk_level="low", action="pass")

    def _get_crisis_message(self) -> str:
        """Get crisis resource message."""
        germany = self.CRISIS_RESOURCES.get("DE", {})
        resources = self.CRISIS_RESOURCES.get("general", {})
        return (
            "I'm concerned about your safety. Please reach out for immediate help:\n"
            "If you're in Germany:\n"
            f"- {germany.get('phone', 'TelefonSeelsorge: 116 123')}\n"
            f"- {germany.get('online', 'Online chat: https://online.telefonseelsorge.de')}\n"
            "If you're outside Germany:\n"
            f"- {resources.get('988', '988 Suicide & Crisis Lifeline')}\n"
            f"- {resources.get('text', 'Crisis Text Line: Text HOME to 741741')}\n"
            "You don't have to go through this alone. Professional help is available."
        )

    def sanitize_input(self, text: str, max_length: int = 1000) -> str:
        """Sanitize user input."""
        # Remove control characters
        text = re.sub(r"[\x00-\x1F\x7F-\x9F]", "", text)
        # Trim and limit length
        text = text.strip()[:max_length]
        return text


_safety_service: SafetyService | None = None


def get_safety_service() -> SafetyService:
    """Get or create safety service singleton."""
    global _safety_service
    if _safety_service is None:
        _safety_service = SafetyService()
    return _safety_service
