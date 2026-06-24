from __future__ import annotations

import base64
from typing import Any

import httpx

from app.config import get_settings

_API_URL = "https://api.speechify.ai/v1/audio/speech"


class SpeechifyError(RuntimeError):
    pass


class SpeechifyClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        voice_id: str | None = None,
        model: str | None = None,
        max_chars: int | None = None,
    ) -> None:
        settings = get_settings().speechify
        self.api_key = api_key if api_key is not None else settings.api_key
        self.voice_id = voice_id or settings.voice_id
        self.model = model or settings.model
        self.max_chars = max_chars or settings.max_chars

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def synthesize_ssml(self, ssml: str) -> dict[str, Any]:
        if not self.api_key:
            raise SpeechifyError("SPEECHIFY_API_KEY is not configured.")

        total_chars = len(ssml)

        if total_chars > self.max_chars:
            raise SpeechifyError(
                f"SSML is {total_chars} characters, which exceeds the "
                f"SPEECHIFY_MAX_CHARS budget of {self.max_chars}.",
            )

        with httpx.Client(timeout=120) as client:
            response = client.post(
                _API_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "input": ssml,
                    "voice_id": self.voice_id,
                    "audio_format": "mp3",
                    "model": self.model,
                },
            )

        if response.status_code >= 400:
            detail = response.text.strip() or response.reason_phrase
            raise SpeechifyError(
                f"Speechify synthesis failed ({response.status_code}): {detail}",
            )

        payload = response.json()
        audio_b64 = payload.get("audio_data")

        if not audio_b64:
            raise SpeechifyError("Speechify response did not include audio_data.")

        return {
            "audio_bytes": base64.b64decode(audio_b64),
            "voice_id": self.voice_id,
            "model": self.model,
            "character_count": total_chars,
        }
