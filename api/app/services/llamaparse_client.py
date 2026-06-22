from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

_API_BASE = "https://api.cloud.llamaindex.ai"
_DEFAULT_TIER = "agentic"
_DEFAULT_POLL_INTERVAL_SECONDS = 2.0
_DEFAULT_MAX_POLL_SECONDS = 600.0
_HTTP_CLIENT_KWARGS = {"timeout": 120, "follow_redirects": True}


class LlamaParseError(RuntimeError):
    pass


def _response_json(response: httpx.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError as exc:
        raise LlamaParseError(
            "LlamaParse returned non-JSON response "
            f"({response.status_code}): {response.text.strip()[:200]}",
        ) from exc

    if not isinstance(payload, dict):
        raise LlamaParseError("LlamaParse returned unexpected JSON payload.")

    return payload


def summarize_llamaparse_api_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a JSON-serializable summary of the LlamaParse job response."""

    summary: dict[str, Any] = {}

    job = payload.get("job")
    if isinstance(job, dict):
        summary["job"] = {
            key: job.get(key)
            for key in ("id", "status", "error_message", "created_at", "updated_at")
            if key in job
        }

    markdown = payload.get("markdown")
    if isinstance(markdown, dict):
        pages_payload = markdown.get("pages")
        if isinstance(pages_payload, list):
            summary["pages"] = [
                {
                    "page": page.get("page") or page.get("page_number") or index,
                    "markdown_length": len(str(page.get("markdown") or page.get("md") or "")),
                }
                for index, page in enumerate(pages_payload, start=1)
                if isinstance(page, dict)
            ]

    markdown_full = payload.get("markdown_full")
    if isinstance(markdown_full, str) and markdown_full.strip():
        summary["markdown_full_length"] = len(markdown_full)

    return summary


@dataclass(frozen=True)
class LlamaParsePage:
    page: int
    markdown: str
    # Structured layout items for this page (type/md/value/level/bbox ...) from the
    # agentic result. Kept alongside markdown so the structuring stages can use the
    # tagged item stream while source-research keeps using the markdown text.
    items: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class LlamaParseResult:
    job_id: str
    pages: list[LlamaParsePage]
    raw_markdown: str
    api_payload: dict[str, Any]
    # Normalized {"page_number", "items"} list consumed by the normalize stage.
    structured_pages: list[dict[str, Any]] = field(default_factory=list)


class LlamaParseClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        tier: str | None = None,
        poll_interval_seconds: float = _DEFAULT_POLL_INTERVAL_SECONDS,
        max_poll_seconds: float = _DEFAULT_MAX_POLL_SECONDS,
    ) -> None:
        resolved_key = api_key or os.getenv("LLAMA_CLOUD_API_KEY")

        if not resolved_key:
            raise RuntimeError("Missing required environment variable: LLAMA_CLOUD_API_KEY")

        self.api_key = resolved_key
        self.tier = tier or os.getenv("LLAMAPARSE_TIER", _DEFAULT_TIER)
        self.poll_interval_seconds = poll_interval_seconds
        self.max_poll_seconds = max_poll_seconds
        self.headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {resolved_key}",
        }

    def parse_pdf(self, *, filename: str, content: bytes) -> LlamaParseResult:
        file_id = self._upload_file(filename=filename, content=content)
        job_id = self._start_parse_job(file_id)
        payload = self._poll_until_complete(job_id)
        pages = self._extract_pages(payload)

        if not pages:
            raise LlamaParseError("LlamaParse returned no markdown pages.")

        raw_markdown = "\n\n".join(
            f"<!-- page:{page.page} -->\n{page.markdown.strip()}"
            for page in pages
            if page.markdown.strip()
        )

        structured_pages = self._extract_structured_pages(payload, pages)

        return LlamaParseResult(
            job_id=job_id,
            pages=pages,
            raw_markdown=raw_markdown,
            api_payload=summarize_llamaparse_api_payload(payload),
            structured_pages=structured_pages,
        )

    def _upload_file(self, *, filename: str, content: bytes) -> str:
        with httpx.Client(**_HTTP_CLIENT_KWARGS) as client:
            response = client.post(
                f"{_API_BASE}/api/v1/beta/files",
                headers=self.headers,
                files={"file": (filename, content, "application/pdf")},
                data={"purpose": "parse"},
            )

        if response.status_code >= 400:
            raise LlamaParseError(
                f"LlamaParse file upload failed ({response.status_code}): {response.text.strip()}",
            )

        payload = _response_json(response)
        file_id = payload.get("id")

        if not isinstance(file_id, str) or not file_id:
            raise LlamaParseError("LlamaParse file upload returned no file id.")

        return file_id

    def _start_parse_job(self, file_id: str) -> str:
        with httpx.Client(**_HTTP_CLIENT_KWARGS) as client:
            response = client.post(
                f"{_API_BASE}/api/v2/parse",
                headers={
                    **self.headers,
                    "Content-Type": "application/json",
                },
                json={
                    "file_id": file_id,
                    "tier": self.tier,
                    "version": "latest",
                },
            )

        if response.status_code >= 400:
            raise LlamaParseError(
                f"LlamaParse job creation failed ({response.status_code}): {response.text.strip()}",
            )

        payload = _response_json(response)
        job = payload.get("job") if isinstance(payload.get("job"), dict) else payload
        job_id = job.get("id") if isinstance(job, dict) else None

        if not isinstance(job_id, str) or not job_id:
            raise LlamaParseError("LlamaParse job creation returned no job id.")

        return job_id

    def _poll_until_complete(self, job_id: str) -> dict[str, Any]:
        deadline = time.monotonic() + self.max_poll_seconds

        while time.monotonic() < deadline:
            with httpx.Client(**_HTTP_CLIENT_KWARGS) as client:
                response = client.get(
                    f"{_API_BASE}/api/v2/parse/{job_id}",
                    headers=self.headers,
                    # Request markdown plus structured per-page items for the
                    # structuring stages (see LlamaParse expand: markdown,items).
                    params={"expand": "markdown,items"},
                )

            if response.status_code >= 400:
                raise LlamaParseError(
                    f"LlamaParse status check failed ({response.status_code}): {response.text.strip()}",
                )

            payload = _response_json(response)
            job = payload.get("job") if isinstance(payload.get("job"), dict) else {}
            status = str(job.get("status") or "").upper()

            if status == "COMPLETED":
                return payload

            if status == "FAILED":
                error_message = job.get("error_message") or "unknown error"
                raise LlamaParseError(f"LlamaParse job failed: {error_message}")

            time.sleep(self.poll_interval_seconds)

        raise LlamaParseError(
            f"LlamaParse job timed out after {self.max_poll_seconds:.0f} seconds.",
        )

    def _extract_pages(self, payload: dict[str, Any]) -> list[LlamaParsePage]:
        markdown = payload.get("markdown")

        if isinstance(markdown, dict):
            pages_payload = markdown.get("pages")

            if isinstance(pages_payload, list):
                pages: list[LlamaParsePage] = []

                for index, page in enumerate(pages_payload, start=1):
                    if not isinstance(page, dict):
                        continue

                    text = page.get("markdown") or page.get("md") or ""
                    page_number = page.get("page") or page.get("page_number") or index
                    items = page.get("items")

                    try:
                        resolved_page = int(page_number)
                    except (TypeError, ValueError):
                        resolved_page = index

                    pages.append(
                        LlamaParsePage(
                            page=resolved_page,
                            markdown=str(text),
                            items=items if isinstance(items, list) else [],
                        ),
                    )

                if pages:
                    return pages

        markdown_full = payload.get("markdown_full")

        if isinstance(markdown_full, str) and markdown_full.strip():
            return [LlamaParsePage(page=1, markdown=markdown_full)]

        return []

    def _extract_structured_pages(
        self,
        payload: dict[str, Any],
        pages: list[LlamaParsePage],
    ) -> list[dict[str, Any]]:
        """Return a [{"page_number", "items"}] list for the structuring stages."""
        candidate = _find_items_pages(payload)
        if candidate:
            structured: list[dict[str, Any]] = []
            for index, page in enumerate(candidate, start=1):
                if not isinstance(page, dict):
                    continue
                items = page.get("items")
                if not isinstance(items, list):
                    continue
                page_number = page.get("page_number") or page.get("page") or index
                try:
                    resolved = int(page_number)
                except (TypeError, ValueError):
                    resolved = index
                structured.append({"page_number": resolved, "items": items})
            if structured:
                return structured

        return [
            {"page_number": page.page, "items": page.items}
            for page in pages
            if page.items
        ]


def _find_items_pages(payload: dict[str, Any]) -> list[Any] | None:
    """Locate a `pages` array whose entries carry `items`, across known nestings."""
    containers: list[Any] = [
        payload.get("items"),
        payload,
        payload.get("result"),
        payload.get("json"),
        payload.get("data"),
        payload.get("layout"),  # legacy/alternate nesting from older integrations
    ]
    for container in containers:
        if not isinstance(container, dict):
            continue
        pages = container.get("pages")
        if isinstance(pages, list) and any(
            isinstance(page, dict) and isinstance(page.get("items"), list) for page in pages
        ):
            return pages
    return None
