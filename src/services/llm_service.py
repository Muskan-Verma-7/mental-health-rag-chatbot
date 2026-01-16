"""LLM service using Groq API with retry logic."""

import asyncio
from typing import List, Dict, Any, Optional
from groq import AsyncGroq
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from ..core.config import get_settings
from ..core.exceptions import LLMException


class LLMService:
    """Service for LLM generation with Groq."""

    def __init__(self):
        """Initialize LLM service."""
        settings = get_settings()
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY.get_secret_value())
        self.model = settings.LLM_MODEL
        self.temperature = settings.LLM_TEMPERATURE
        self.max_tokens = settings.LLM_MAX_TOKENS
        self.timeout = settings.LLM_TIMEOUT

    def _build_system_prompt(self) -> str:
        """Build system prompt for empathetic mental health coach."""
        return """You are a supportive and empathetic mental health coach. Your role is to:
- Listen actively and validate the user's feelings
- Provide evidence-based coping strategies from therapy resources
- Use a warm, non-judgmental tone
- Encourage professional help when appropriate
- Never diagnose or replace professional therapy

Use the provided therapy document excerpts to inform your responses. Stay within the scope of general mental health support."""

    def _build_prompt(
        self,
        query: str,
        context: List[str],
        history: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, str]]:
        """Build conversation prompt with context and optional history."""
        context_text = "\n\n".join(
            [f"Document excerpt {i+1}:\n{chunk}" for i, chunk in enumerate(context)]
        )

        messages = [
            {"role": "system", "content": self._build_system_prompt()},
        ]

        if history:
            allowed_roles = {"user", "assistant"}
            for msg in history[-6:]:
                role = msg.get("role")
                content = (msg.get("content") or "").strip()
                if role in allowed_roles and content:
                    messages.append(
                        {
                            "role": role,
                            "content": content[:1000],
                        }
                    )

        messages.append(
            {
                "role": "user",
                "content": f"""Based on the following therapy document excerpts, provide a supportive response to the user's concern.

Therapy Resources:
{context_text}

User's concern: {query}

Provide a helpful, empathetic response using the therapy resources above.""",
            }
        )
        return messages

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def generate(
        self,
        query: str,
        context: List[str],
        history: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """Generate response using LLM."""
        try:
            messages = self._build_prompt(query, context, history=history)
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                ),
                timeout=self.timeout,
            )
            return response.choices[0].message.content
        except asyncio.TimeoutError:
            raise LLMException(f"LLM generation timed out after {self.timeout}s")
        except Exception as e:
            raise LLMException(f"LLM generation failed: {e}")


_llm_service: LLMService | None = None


def get_llm_service() -> LLMService:
    """Get or create LLM service singleton."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
