"""ElevenLabs text-to-speech with character-level timing.

Narration is synthesized one chapter clip at a time via
POST /v1/text-to-speech/{voice_id}/with-timestamps, which returns the audio
plus per-character start/end times. Character times are folded into word
timings using the same whitespace tokenization the Reader applies to the
clip's plain text. When a chapter exceeds the character cap it is packed into
multiple clips on paragraph boundaries.
"""

from __future__ import annotations

import base64
import logging
import time
from dataclasses import dataclass
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

_API_BASE = "https://api.elevenlabs.io/v1/text-to-speech"
_RETRYABLE_STATUS_CODES = {429, 502, 503, 504}
_RETRY_BACKOFF_SECONDS = 5

# Continuity hints for request stitching across paragraph boundaries. Not all
# models accept them — eleven_v3 rejects the request with an
# "unsupported_model" validation error — so they are stripped for those models
# up front, and stripped reactively if the API rejects them anyway.
_STITCHING_KEYS = ("previous_request_ids", "previous_text", "next_text")
_MODELS_WITHOUT_STITCHING_PREFIXES = ("eleven_v3",)


def model_supports_stitching(model_id: str) -> bool:
    normalized = (model_id or "").strip().lower()
    return not normalized.startswith(_MODELS_WITHOUT_STITCHING_PREFIXES)


class ElevenLabsError(RuntimeError):
    pass


@dataclass(frozen=True)
class WordTiming:
    index: int
    word: str
    start: float
    end: float

    def to_dict(self) -> dict[str, Any]:
        return {"i": self.index, "w": self.word, "s": self.start, "e": self.end}


@dataclass(frozen=True)
class NarrationResult:
    audio: bytes
    words: list[WordTiming]
    duration_seconds: float
    request_id: str | None
    character_cost: int


def words_from_alignment(
    characters: list[str],
    start_times: list[float],
    end_times: list[float],
) -> list[WordTiming]:
    """Group per-character timings into words on whitespace boundaries.

    The characters array reconstructs the exact text sent, so grouping
    non-whitespace runs mirrors `text.split()` — word N here is word N in the
    Reader's token stream.
    """
    words: list[WordTiming] = []
    current = ""
    word_start = 0.0

    for char, start, end in zip(characters, start_times, end_times, strict=False):
        if char.isspace():
            if current:
                words.append(WordTiming(len(words), current, word_start, prev_end))
                current = ""
            continue
        if not current:
            word_start = start
        current += char
        prev_end = end

    if current:
        words.append(WordTiming(len(words), current, word_start, prev_end))

    return words


class ElevenLabsClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        voice_id: str | None = None,
        model_id: str | None = None,
        output_format: str | None = None,
        request_timeout_seconds: int | None = None,
        max_retries: int | None = None,
    ) -> None:
        settings = get_settings().narration
        self.api_key = api_key if api_key is not None else settings.elevenlabs_api_key
        self.voice_id = voice_id or settings.voice_id
        self.model_id = model_id or settings.model_id
        self.output_format = output_format or settings.output_format
        self.request_timeout_seconds = (
            request_timeout_seconds or settings.request_timeout_seconds
        )
        self.max_retries = max_retries or settings.max_retries
        self.provider = "elevenlabs"
        self.max_segment_chars = settings.elevenlabs_max_segment_chars

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def _timeout(self) -> httpx.Timeout:
        return httpx.Timeout(
            connect=30.0,
            read=float(self.request_timeout_seconds),
            write=30.0,
            pool=30.0,
        )

    def synthesize_with_timestamps(
        self,
        text: str,
        *,
        previous_request_ids: list[str] | None = None,
        previous_text: str | None = None,
        next_text: str | None = None,
        client: httpx.Client | None = None,
    ) -> NarrationResult:
        if not self.api_key:
            raise ElevenLabsError("ELEVENLABS_API_KEY is not configured.")

        body: dict[str, Any] = {"text": text, "model_id": self.model_id}
        if model_supports_stitching(self.model_id):
            if previous_request_ids:
                body["previous_request_ids"] = previous_request_ids[-3:]
            elif previous_text:
                body["previous_text"] = previous_text
            if next_text:
                body["next_text"] = next_text

        if client is not None:
            return self._post(client, body, text)
        with httpx.Client(timeout=self._timeout()) as owned:
            return self._post(owned, body, text)

    def _post(self, client: httpx.Client, body: dict[str, Any], text: str) -> NarrationResult:
        last_error: str | None = None

        for attempt in range(self.max_retries):
            try:
                response = client.post(
                    f"{_API_BASE}/{self.voice_id}/with-timestamps",
                    params={"output_format": self.output_format},
                    headers={"xi-api-key": self.api_key or ""},
                    json=body,
                )
            except (httpx.ReadTimeout, httpx.ConnectTimeout) as exc:
                last_error = f"timeout: {exc}"
                if attempt >= self.max_retries - 1:
                    break
                self._backoff(attempt, last_error)
                continue

            if response.status_code < 400:
                return self._parse(response, text)

            last_error = f"{response.status_code}: {response.text.strip()[:500]}"

            # The model rejected the continuity hints (e.g. a model outside the
            # known no-stitching list): drop them and retry immediately —
            # narration quality degrades slightly at the boundary, but the run
            # keeps going.
            if (
                response.status_code == 400
                and "unsupported_model" in response.text
                and any(key in body for key in _STITCHING_KEYS)
            ):
                for key in _STITCHING_KEYS:
                    body.pop(key, None)
                logger.warning(
                    "ElevenLabs model %s rejected request-stitching hints; "
                    "retrying without them.",
                    self.model_id,
                )
                continue

            if response.status_code not in _RETRYABLE_STATUS_CODES:
                break
            if attempt >= self.max_retries - 1:
                break
            self._backoff(attempt, last_error)

        raise ElevenLabsError(
            f"ElevenLabs synthesis failed after {self.max_retries} attempt(s): {last_error}",
        )

    def _backoff(self, attempt: int, reason: str) -> None:
        wait_seconds = _RETRY_BACKOFF_SECONDS * (2**attempt)
        logger.warning(
            "ElevenLabs synthesis attempt %d/%d failed (%s); retrying in %ds",
            attempt + 1,
            self.max_retries,
            reason,
            wait_seconds,
        )
        time.sleep(wait_seconds)

    def _parse(self, response: httpx.Response, text: str) -> NarrationResult:
        payload = response.json()
        audio_b64 = payload.get("audio_base64")
        if not audio_b64:
            raise ElevenLabsError("ElevenLabs response missing audio_base64.")
        audio = base64.b64decode(audio_b64)

        alignment = payload.get("alignment") or payload.get("normalized_alignment") or {}
        characters = alignment.get("characters") or []
        starts = alignment.get("character_start_times_seconds") or []
        ends = alignment.get("character_end_times_seconds") or []
        words = words_from_alignment(characters, starts, ends)

        expected = len(text.split())
        if words and len(words) != expected:
            logger.warning(
                "ElevenLabs alignment produced %d words for a %d-word segment; "
                "highlighting may drift within this paragraph.",
                len(words),
                expected,
            )

        duration = ends[-1] if ends else (words[-1].end if words else 0.0)

        raw_cost = response.headers.get("character-cost")
        try:
            character_cost = int(float(raw_cost)) if raw_cost else len(text)
        except ValueError:
            character_cost = len(text)

        return NarrationResult(
            audio=audio,
            words=words,
            duration_seconds=float(duration),
            request_id=response.headers.get("request-id"),
            character_cost=character_cost,
        )
