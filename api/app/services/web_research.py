from __future__ import annotations

import os
from typing import Any

import httpx


class WebResearchClient:
    def __init__(self, *, api_key: str | None = None) -> None:
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def search(self, query: str, *, max_results: int = 5) -> list[dict[str, str]]:
        if not self.api_key:
            return []

        with httpx.Client(timeout=30) as client:
            response = client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self.api_key,
                    "query": query,
                    "max_results": max_results,
                    "include_answer": False,
                },
            )

        if response.status_code >= 400:
            detail = response.text.strip() or response.reason_phrase
            raise RuntimeError(f"Tavily search failed ({response.status_code}): {detail}")

        payload = response.json()
        results = payload.get("results", [])

        if not isinstance(results, list):
            return []

        normalized: list[dict[str, str]] = []

        for result in results:
            if not isinstance(result, dict):
                continue

            normalized.append(
                {
                    "title": str(result.get("title") or ""),
                    "url": str(result.get("url") or ""),
                    "content": str(result.get("content") or ""),
                },
            )

        return normalized


def build_research_query(*, title: str | None, identifier: str | None) -> str:
    parts = [part for part in [title, identifier] if part]

    if not parts:
        return ""

    return " ".join(parts)
