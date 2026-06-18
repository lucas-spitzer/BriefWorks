from __future__ import annotations

import logging
import os
import re
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# eleven_v3 accepts up to ~3,000 characters per request. Stay under that so a
# single oversized paragraph never trips the limit, and so pause tags are never
# split across requests.
DEFAULT_CHUNK_CHARS = 2_500
DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # ElevenLabs public "Rachel" voice
DEFAULT_MODEL_ID = "eleven_v3"
DEFAULT_MAX_CHARS = 200_000
DEFAULT_OUTPUT_FORMAT = "mp3_44100_128"
DEFAULT_REQUEST_TIMEOUT_SECONDS = 600
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_BACKOFF_SECONDS = 5

_RETRYABLE_STATUS_CODES = {429, 502, 503, 504}

_API_BASE = "https://api.elevenlabs.io/v1/text-to-speech"

# Split points, preferring paragraph then sentence boundaries.
_PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


class ElevenLabsError(RuntimeError):
    pass


def _split_into_blocks(text: str) -> list[str]:
    blocks = [block.strip() for block in _PARAGRAPH_SPLIT_RE.split(text) if block.strip()]
    return blocks or ([text.strip()] if text.strip() else [])


def _split_long_block(block: str, *, max_chars: int) -> list[str]:
    if len(block) <= max_chars:
        return [block]

    pieces: list[str] = []
    current = ""

    for sentence in _SENTENCE_SPLIT_RE.split(block):
        candidate = f"{current} {sentence}".strip() if current else sentence

        if len(candidate) <= max_chars:
            current = candidate
            continue

        if current:
            pieces.append(current)

        # A single sentence longer than the limit is hard-wrapped on whitespace
        # so we never cut through the middle of a "[pause]" style tag.
        if len(sentence) > max_chars:
            pieces.extend(_hard_wrap(sentence, max_chars=max_chars))
            current = ""
        else:
            current = sentence

    if current:
        pieces.append(current)

    return pieces


def _hard_wrap(text: str, *, max_chars: int) -> list[str]:
    pieces: list[str] = []
    current = ""

    for word in text.split(" "):
        candidate = f"{current} {word}".strip() if current else word

        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                pieces.append(current)
            current = word

    if current:
        pieces.append(current)

    return pieces


def chunk_text(text: str, *, max_chars: int = DEFAULT_CHUNK_CHARS) -> list[str]:
    """Split narration text into <= max_chars chunks on safe boundaries.

    Never splits inside a "[tag]" because chunking happens on paragraph and
    sentence boundaries (and word boundaries as a last resort), and ElevenLabs
    audio tags never span those boundaries in our emitter output.
    """

    chunks: list[str] = []
    current = ""

    for block in _split_into_blocks(text):
        for piece in _split_long_block(block, max_chars=max_chars):
            candidate = f"{current}\n\n{piece}".strip() if current else piece

            if len(candidate) <= max_chars:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                current = piece

    if current:
        chunks.append(current)

    return chunks


class ElevenLabsClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        voice_id: str | None = None,
        model_id: str | None = None,
        max_chars: int | None = None,
        chunk_chars: int | None = None,
        request_timeout_seconds: int | None = None,
        max_retries: int | None = None,
        output_format: str = DEFAULT_OUTPUT_FORMAT,
    ) -> None:
        self.api_key = api_key if api_key is not None else os.getenv("ELEVENLABS_API_KEY")
        self.voice_id = voice_id or os.getenv("ELEVENLABS_VOICE_ID") or DEFAULT_VOICE_ID
        self.model_id = model_id or os.getenv("ELEVENLABS_MODEL_ID") or DEFAULT_MODEL_ID
        self.max_chars = max_chars or int(
            os.getenv("ELEVENLABS_MAX_CHARS", str(DEFAULT_MAX_CHARS)),
        )
        self.chunk_chars = chunk_chars or int(
            os.getenv("ELEVENLABS_CHUNK_CHARS", str(DEFAULT_CHUNK_CHARS)),
        )
        self.request_timeout_seconds = request_timeout_seconds or int(
            os.getenv(
                "ELEVENLABS_REQUEST_TIMEOUT_SECONDS",
                str(DEFAULT_REQUEST_TIMEOUT_SECONDS),
            ),
        )
        self.max_retries = max_retries or int(
            os.getenv("ELEVENLABS_MAX_RETRIES", str(DEFAULT_MAX_RETRIES)),
        )
        self.output_format = output_format

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def _request_timeout(self) -> httpx.Timeout:
        return httpx.Timeout(
            connect=30.0,
            read=float(self.request_timeout_seconds),
            write=30.0,
            pool=30.0,
        )

    def synthesize(self, text: str, *, client: httpx.Client | None = None) -> bytes:
        if not self.api_key:
            raise ElevenLabsError("ELEVENLABS_API_KEY is not configured.")

        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                if client is None:
                    with httpx.Client(timeout=self._request_timeout()) as owned_client:
                        return self._post_synthesis(owned_client, text)

                return self._post_synthesis(client, text)
            except (httpx.ReadTimeout, httpx.ConnectTimeout) as exc:
                last_error = exc
                if attempt >= self.max_retries - 1:
                    break

                wait_seconds = DEFAULT_RETRY_BACKOFF_SECONDS * (2**attempt)
                logger.warning(
                    "ElevenLabs synthesis timed out on attempt %d/%d; retrying in %ds",
                    attempt + 1,
                    self.max_retries,
                    wait_seconds,
                )
                time.sleep(wait_seconds)

        raise ElevenLabsError(
            f"ElevenLabs synthesis timed out after {self.max_retries} attempt(s).",
        ) from last_error

    def _post_synthesis(self, client: httpx.Client, text: str) -> bytes:
        last_response: httpx.Response | None = None

        for attempt in range(self.max_retries):
            response = client.post(
                f"{_API_BASE}/{self.voice_id}",
                params={"output_format": self.output_format},
                headers={
                    "xi-api-key": self.api_key or "",
                    "accept": "audio/mpeg",
                },
                json={"text": text, "model_id": self.model_id},
            )
            last_response = response

            if response.status_code < 400:
                return response.content

            if response.status_code not in _RETRYABLE_STATUS_CODES:
                break

            if attempt >= self.max_retries - 1:
                break

            wait_seconds = DEFAULT_RETRY_BACKOFF_SECONDS * (2**attempt)
            logger.warning(
                "ElevenLabs synthesis returned %d on attempt %d/%d; retrying in %ds",
                response.status_code,
                attempt + 1,
                self.max_retries,
                wait_seconds,
            )
            time.sleep(wait_seconds)

        detail = (last_response.text.strip() if last_response else "") or "unknown error"
        status_code = last_response.status_code if last_response else 0
        raise ElevenLabsError(
            f"ElevenLabs synthesis failed ({status_code}): {detail}",
        )

    def synthesize_long_text(self, text: str) -> dict[str, Any]:
        """Chunk text, synthesize each chunk, and concatenate the MP3 bytes.

        Returns the joined audio plus metadata for the artifact manifest.
        """

        total_chars = len(text)

        if total_chars > self.max_chars:
            raise ElevenLabsError(
                f"Narration text is {total_chars} characters, which exceeds the "
                f"ELEVENLABS_MAX_CHARS budget of {self.max_chars}. Raise the budget "
                "intentionally for large jobs.",
            )

        chunks = chunk_text(text, max_chars=self.chunk_chars)
        audio = bytearray()

        with httpx.Client(timeout=self._request_timeout()) as client:
            for index, chunk in enumerate(chunks, start=1):
                logger.info(
                    "ElevenLabs synthesizing chunk %d/%d (%d chars)",
                    index,
                    len(chunks),
                    len(chunk),
                )
                audio.extend(self.synthesize(chunk, client=client))

        return {
            "audio_bytes": bytes(audio),
            "voice_id": self.voice_id,
            "model_id": self.model_id,
            "character_count": total_chars,
            "request_count": len(chunks),
        }
