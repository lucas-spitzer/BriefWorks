from __future__ import annotations

import base64
from typing import Any

import pytest

from app.services.api_pricing import cost_elevenlabs_usage, cost_speechify_usage
from app.services.speechify_client import SpeechifyClient, words_from_speech_marks
from app.services.tts.catalog import TTS_MODEL_CATALOG, get_tts_catalog_model
from app.services.tts.factory import (
    get_tts_client,
    narration_override_from_rows,
    reset_narration_override,
    set_narration_override,
)
from app.tts_defaults import tts_provider_for_model


def test_tts_provider_for_model() -> None:
    assert tts_provider_for_model("simba-3.2") == "speechify"
    assert tts_provider_for_model("simba-3.0") == "speechify"
    assert tts_provider_for_model("eleven_v3") == "elevenlabs"
    assert tts_provider_for_model("eleven_multilingual_v2") == "elevenlabs"


def test_tts_catalog_only_ships_simba_32_and_eleven_v3() -> None:
    models = {entry.model for entry in TTS_MODEL_CATALOG}
    assert models == {"simba-3.2", "eleven_v3"}
    simba = get_tts_catalog_model("simba-3.2")
    eleven = get_tts_catalog_model("eleven_v3")
    assert simba is not None and simba.price_per_million == 10.0
    assert simba.capability_tier == 2
    assert eleven is not None and eleven.price_per_million == 100.0
    assert eleven.capability_tier == 5
    assert eleven.default_voice_id == "4YYIPFl9wE5c4L2eu2Gb"
    assert eleven.voices[0].display_name == "Burt Reynolds"
    assert get_tts_catalog_model("simba-3.0") is None
    assert get_tts_catalog_model("eleven_multilingual_v2") is None


def test_tts_list_prices_per_million_characters(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SPEECHIFY_PRICE_PER_CHARACTER", raising=False)
    monkeypatch.delenv("ELEVENLABS_PRICE_PER_CHARACTER", raising=False)

    speechify = cost_speechify_usage(model="simba-3.2", character_count=1_000_000)
    eleven = cost_elevenlabs_usage(model="eleven_v3", character_count=1_000_000)

    assert speechify["cost_usd"] == 10.0
    assert eleven["cost_usd"] == 100.0


def test_words_from_speech_marks_converts_ms_to_seconds() -> None:
    text = "Hello, welcome to Speechify"
    marks = {
        "chunks": [
            {"start": 0, "end": 6, "start_time": 125, "end_time": 375, "value": "Hello,"},
            {"start": 7, "end": 14, "start_time": 375, "end_time": 750, "value": "welcome"},
            {"start": 15, "end": 17, "start_time": 750, "end_time": 875, "value": "to"},
            {"start": 18, "end": 27, "start_time": 875, "end_time": 1850, "value": "Speechify"},
        ],
    }

    words = words_from_speech_marks(marks, text)

    assert [word.word for word in words] == ["Hello,", "welcome", "to", "Speechify"]
    assert words[0].start == 0.125
    assert words[0].end == 0.375
    assert words[-1].end == 1.85
    assert words[0].index == 0


def test_words_from_speech_marks_accepts_flat_list() -> None:
    words = words_from_speech_marks(
        [{"value": "Hello", "start_time": 0, "end_time": 400}],
        "Hello",
    )
    assert len(words) == 1
    assert words[0].end == 0.4


def test_get_tts_client_routes_by_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPEECHIFY_API_KEY", "sf-key")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "el-key")
    from app.config import get_settings

    get_settings.cache_clear()

    speechify = get_tts_client(model="simba-3.2", voice_id="hugh_32")
    eleven = get_tts_client(model="eleven_v3", voice_id="voice-1")

    assert speechify.provider == "speechify"
    assert speechify.voice_id == "hugh_32"
    assert eleven.provider == "elevenlabs"
    assert eleven.model_id == "eleven_v3"

    get_settings.cache_clear()


def test_narration_override_from_rows() -> None:
    override = narration_override_from_rows(
        [
            {"stage_action": "wiki_structuring", "provider": "openai", "model": "gpt-5.4"},
            {
                "stage_action": "audio_narration",
                "provider": "speechify",
                "model": "simba-3.2",
                "voice_id": "beatrice_32",
            },
        ],
    )
    assert override is not None
    assert override.voice_id == "beatrice_32"
    token = set_narration_override(override)
    try:
        client = get_tts_client()
        assert client.provider == "speechify"
        assert client.voice_id == "beatrice_32"
    finally:
        reset_narration_override(token)


def test_speechify_batch_parse(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPEECHIFY_API_KEY", "sf-key")
    from app.config import get_settings

    get_settings.cache_clear()

    class _FakeResponse:
        status_code = 200
        headers: dict[str, str] = {}
        text = ""

        def json(self) -> dict[str, Any]:
            return {
                "audio_data": base64.b64encode(b"mp3").decode(),
                "billable_characters_count": 5,
                "speech_marks": {
                    "end_time": 800,
                    "chunks": [
                        {"value": "Hello", "start_time": 0, "end_time": 400},
                        {"value": "world", "start_time": 400, "end_time": 800},
                    ],
                },
            }

    class _FakeHttp:
        def post(self, url: str, *, headers: Any, json: dict[str, Any]) -> _FakeResponse:
            assert "speech" in url
            assert json["model"] == "simba-3.2"
            assert json["voice_id"] == "hugh_32"
            return _FakeResponse()

    client = SpeechifyClient(api_key="k", voice_id="hugh_32", model_id="simba-3.2")
    result = client.synthesize_with_timestamps("Hello world", client=_FakeHttp())  # type: ignore[arg-type]

    assert result.audio == b"mp3"
    assert [word.word for word in result.words] == ["Hello", "world"]
    assert result.duration_seconds == 0.8
    assert result.character_cost == 5

    get_settings.cache_clear()
