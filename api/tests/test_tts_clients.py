import base64

import httpx
import pytest

from app.services.elevenlabs_client import (
    DEFAULT_CHUNK_CHARS,
    ElevenLabsClient,
    ElevenLabsError,
    chunk_text,
)
from app.services.speechify_client import SpeechifyClient, SpeechifyError


def _patch_httpx(monkeypatch, handler) -> dict:
    """Route httpx.Client traffic through a MockTransport and count calls."""

    state = {"calls": 0}
    transport = httpx.MockTransport(handler)
    real_client = httpx.Client

    def factory(*args, **kwargs):
        kwargs["transport"] = transport
        return real_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", factory)
    return state


def test_chunk_text_respects_max_and_keeps_tags_intact() -> None:
    paragraph = "[focused] " + ("word " * 800).strip()
    text = "\n\n".join([paragraph, paragraph, paragraph])

    chunks = chunk_text(text, max_chars=DEFAULT_CHUNK_CHARS)

    assert len(chunks) > 1
    assert all(len(chunk) <= DEFAULT_CHUNK_CHARS for chunk in chunks)
    # A bracketed tag is never split across chunk boundaries.
    for chunk in chunks:
        assert chunk.count("[") == chunk.count("]")


def test_elevenlabs_synthesize_long_text_concatenates_chunks(monkeypatch) -> None:
    state = {"calls": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        state["calls"] += 1
        return httpx.Response(200, content=b"MP3")

    _patch_httpx(monkeypatch, handler)

    client = ElevenLabsClient(api_key="test-key")
    long_text = "\n\n".join(["sentence. " * 400] * 3)

    result = client.synthesize_long_text(long_text)

    assert state["calls"] >= 2
    assert result["request_count"] == state["calls"]
    assert result["audio_bytes"] == b"MP3" * state["calls"]
    assert result["voice_id"] == client.voice_id


def test_elevenlabs_enforces_char_budget(monkeypatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover - not called
        return httpx.Response(200, content=b"MP3")

    _patch_httpx(monkeypatch, handler)

    client = ElevenLabsClient(api_key="test-key", max_chars=10)

    with pytest.raises(ElevenLabsError):
        client.synthesize_long_text("x" * 50)


def test_elevenlabs_requires_api_key() -> None:
    client = ElevenLabsClient(api_key="")

    assert client.enabled is False
    with pytest.raises(ElevenLabsError):
        client.synthesize("hello")


def test_elevenlabs_retries_on_read_timeout(monkeypatch) -> None:
    state = {"calls": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        state["calls"] += 1
        if state["calls"] == 1:
            raise httpx.ReadTimeout("timed out")
        return httpx.Response(200, content=b"MP3")

    _patch_httpx(monkeypatch, handler)
    monkeypatch.setattr("app.services.elevenlabs_client.time.sleep", lambda _: None)

    client = ElevenLabsClient(api_key="test-key", max_retries=2)
    audio = client.synthesize("hello")

    assert audio == b"MP3"
    assert state["calls"] == 2


def test_elevenlabs_retries_on_rate_limit(monkeypatch) -> None:
    state = {"calls": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        state["calls"] += 1
        if state["calls"] == 1:
            return httpx.Response(429, text="rate limited")
        return httpx.Response(200, content=b"MP3")

    _patch_httpx(monkeypatch, handler)
    monkeypatch.setattr("app.services.elevenlabs_client.time.sleep", lambda _: None)

    client = ElevenLabsClient(api_key="test-key", max_retries=2)
    audio = client.synthesize("hello")

    assert audio == b"MP3"
    assert state["calls"] == 2


def test_speechify_synthesize_ssml_decodes_audio(monkeypatch) -> None:
    audio = b"\x00\x01speechify-mp3"
    encoded = base64.b64encode(audio).decode("ascii")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"audio_data": encoded, "audio_format": "mp3"})

    _patch_httpx(monkeypatch, handler)

    client = SpeechifyClient(api_key="test-key")
    result = client.synthesize_ssml("<speak>Hello</speak>")

    assert result["audio_bytes"] == audio
    assert result["voice_id"] == client.voice_id
    assert result["model"] == client.model


def test_speechify_requires_api_key() -> None:
    client = SpeechifyClient(api_key="")

    assert client.enabled is False
    with pytest.raises(SpeechifyError):
        client.synthesize_ssml("<speak>Hi</speak>")


def test_speechify_raises_without_audio_data(monkeypatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": True})

    _patch_httpx(monkeypatch, handler)

    client = SpeechifyClient(api_key="test-key")

    with pytest.raises(SpeechifyError):
        client.synthesize_ssml("<speak>Hi</speak>")
