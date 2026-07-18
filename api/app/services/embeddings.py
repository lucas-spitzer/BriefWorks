from __future__ import annotations

from typing import Protocol, runtime_checkable

from openai import OpenAI

from app.config import get_settings


@runtime_checkable
class EmbeddingClient(Protocol):
    """Minimal embedding interface so stages type against this, not a provider."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text, in order."""
        ...


class OpenAIEmbeddingClient:
    def __init__(self, *, api_key: str | None = None, model: str | None = None) -> None:
        settings = get_settings()
        resolved_key = api_key or settings.llm.openai_api_key
        if not resolved_key:
            raise RuntimeError("Missing required environment variable: OPENAI_API_KEY")

        self.model = model or settings.intellex.embedding_model
        self.client = OpenAI(api_key=resolved_key)

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = self.client.embeddings.create(model=self.model, input=texts)
        return [item.embedding for item in response.data]


def get_embedding_client() -> EmbeddingClient:
    return OpenAIEmbeddingClient()


def to_pgvector_literal(embedding: list[float]) -> str:
    """Format a vector for a pgvector column / function arg (e.g. '[0.1,0.2]')."""
    return "[" + ",".join(repr(value) for value in embedding) + "]"
