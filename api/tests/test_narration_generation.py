"""Tests for the generate-narration stage's alignment and pipeline wiring."""

import base64
import json
from typing import Any

from app.intellex.structuring.chunk import display_markdown, flatten_markdown
from app.pipeline import SUPPORTED_TARGET_ARTIFACTS, build_pipeline
from app.services.elevenlabs_client import (
    ElevenLabsClient,
    model_supports_stitching,
    words_from_alignment,
)


def test_narration_audio_is_a_supported_target() -> None:
    assert "narration_audio" in SUPPORTED_TARGET_ARTIFACTS


def test_build_pipeline_appends_generate_narration_step() -> None:
    pipeline = build_pipeline(["narration_audio"])
    assert [step["step"] for step in pipeline][-1] == "generate-narration"


def test_words_from_alignment_groups_on_whitespace() -> None:
    text = "Hi there, world."
    characters = list(text)
    starts = [i * 0.1 for i in range(len(characters))]
    ends = [i * 0.1 + 0.1 for i in range(len(characters))]

    words = words_from_alignment(characters, starts, ends)

    assert [w.word for w in words] == text.split()
    assert words[0].index == 0
    assert words[0].start == 0.0
    # "Hi" ends when its last character ('i', index 1) ends.
    assert words[0].end == starts[1] + 0.1
    # Word count parity with the Reader's tokenization of the plain text.
    assert len(words) == len(text.split())


def test_words_from_alignment_handles_empty() -> None:
    assert words_from_alignment([], [], []) == []


def test_progress_output_summary_is_fraction() -> None:
    from app.worker.narration_executor import _progress_output

    output = _progress_output(
        done=2,
        total=280,
        narrated=2,
        reused=0,
        skipped=0,
        character_count=209,
        voice_id="voice-1",
        model_id="eleven_v3",
    )

    assert output["summary"] == "2/280 segments"
    assert output["segments_done"] == 2
    assert output["segments_total"] == 280
    assert output["segments_narrated"] == 2


def test_display_markdown_keeps_emphasis_and_word_parity() -> None:
    md = "The  *testing* effect is **real**."
    display = display_markdown(md)

    assert display == "The *testing* effect is **real**."
    assert len(display.split()) == len(flatten_markdown(md).split())


def test_display_markdown_none_when_plain() -> None:
    assert display_markdown("No emphasis here.") is None
    # Sup tags are stripped from both copies, so the md adds nothing.
    assert display_markdown("Footnote<sup>1</sup> text.") is None


# --- Request-stitching model support ----------------------------------------


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict[str, Any] | None = None, text: str = ""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text or json.dumps(self._payload)
        self.headers: dict[str, str] = {}

    def json(self) -> dict[str, Any]:
        return self._payload


class _FakeHttpClient:
    """Captures request bodies; yields queued responses in order."""

    def __init__(self, responses: list[_FakeResponse]) -> None:
        self.responses = responses
        self.bodies: list[dict[str, Any]] = []

    def post(self, url: str, *, params: Any, headers: Any, json: dict[str, Any]) -> _FakeResponse:
        self.bodies.append(dict(json))
        return self.responses[min(len(self.bodies) - 1, len(self.responses) - 1)]


def _ok_response() -> _FakeResponse:
    text = "Hello world"
    characters = list(text)
    return _FakeResponse(
        200,
        {
            "audio_base64": base64.b64encode(b"mp3").decode(),
            "alignment": {
                "characters": characters,
                "character_start_times_seconds": [i * 0.1 for i in range(len(characters))],
                "character_end_times_seconds": [i * 0.1 + 0.1 for i in range(len(characters))],
            },
        },
    )


def test_model_supports_stitching_flags_v3() -> None:
    assert not model_supports_stitching("eleven_v3")
    assert not model_supports_stitching("eleven_v3_preview")
    assert model_supports_stitching("eleven_multilingual_v2")
    assert model_supports_stitching("eleven_flash_v2_5")


def test_v3_requests_omit_stitching_hints() -> None:
    client = ElevenLabsClient(api_key="k", voice_id="v", model_id="eleven_v3")
    fake = _FakeHttpClient([_ok_response()])

    result = client.synthesize_with_timestamps(
        "Hello world",
        previous_request_ids=["r1"],
        next_text="Next paragraph.",
        client=fake,  # type: ignore[arg-type]
    )

    assert len(fake.bodies) == 1
    body = fake.bodies[0]
    assert "previous_request_ids" not in body
    assert "previous_text" not in body
    assert "next_text" not in body
    assert [w.word for w in result.words] == ["Hello", "world"]


def test_unsupported_model_rejection_strips_hints_and_retries() -> None:
    # A model we believe supports stitching gets rejected anyway: the client
    # must strip the hints and immediately retry instead of failing the run.
    rejection = _FakeResponse(
        400,
        text=json.dumps(
            {
                "detail": {
                    "type": "validation_error",
                    "code": "unsupported_model",
                    "message": "Providing previous_text or next_text is not yet supported",
                }
            }
        ),
    )
    client = ElevenLabsClient(api_key="k", voice_id="v", model_id="eleven_multilingual_v2")
    fake = _FakeHttpClient([rejection, _ok_response()])

    result = client.synthesize_with_timestamps(
        "Hello world",
        previous_request_ids=["r1"],
        next_text="Next paragraph.",
        client=fake,  # type: ignore[arg-type]
    )

    assert len(fake.bodies) == 2
    assert "previous_request_ids" in fake.bodies[0]
    assert "next_text" in fake.bodies[0]
    assert "previous_request_ids" not in fake.bodies[1]
    assert "next_text" not in fake.bodies[1]
    assert [w.word for w in result.words] == ["Hello", "world"]


# --- Narration artifact JSON manifest ----------------------------------------


class _FakeWorkerDb:
    def __init__(self, narration_rows: list[dict[str, Any]]) -> None:
        self.narration_rows = narration_rows
        self.created_artifacts: list[dict[str, Any]] = []
        self.updated_artifacts: list[tuple[str, dict[str, Any]]] = []

    def list_narration_segments_for_source(self, source_id: str, voice_id: str):
        return self.narration_rows

    def create_artifact(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.created_artifacts.append(payload)
        return {**payload, "id": "art-1"}

    def update_artifact(self, artifact_id: str, payload: dict[str, Any]):
        self.updated_artifacts.append((artifact_id, payload))
        return payload


class _FakeWorkerStorage:
    sources_bucket = "sources"

    def __init__(self) -> None:
        self.uploads: dict[str, bytes] = {}
        self.upload_content_types: dict[str, str] = {}
        self.upload_buckets: dict[str, str] = {}

    def upload(
        self,
        path: str,
        content: bytes,
        *,
        bucket: str | None = None,
        content_type: str = "application/octet-stream",
    ) -> None:
        self.uploads[path] = content
        self.upload_content_types[path] = content_type
        self.upload_buckets[path] = bucket or self.sources_bucket


def test_publish_artifact_writes_json_manifest() -> None:
    from app.worker.narration_executor import NarrationStageExecutor

    rows = [
        {
            "segment_id": "seg-a",
            "audio_path": "workspaces/ws-1/sources/src-1/narration/v/seg-a.mp3",
            "duration_seconds": 2.5,
            "character_count": 40,
            "words": [{"i": 0, "w": "Hello", "s": 0.0, "e": 0.5}],
        },
        {
            "segment_id": "seg-b",
            "audio_path": "workspaces/ws-1/sources/src-1/narration/v/seg-b.mp3",
            "duration_seconds": 3.0,
            "character_count": 50,
            "words": [{"i": 0, "w": "World", "s": 0.0, "e": 0.6}],
        },
    ]
    db = _FakeWorkerDb(rows)
    storage = _FakeWorkerStorage()
    client = ElevenLabsClient(api_key="k", voice_id="voice-1", model_id="eleven_v3")
    executor = NarrationStageExecutor(
        db=db, storage=storage, client=client, max_segment_chars=9500  # type: ignore[arg-type]
    )

    chapters = [
        {
            "id": "ch-1",
            "title": "Chapter One",
            "sequence_index": 0,
            "segment_ids": ["seg-h", "seg-a", "seg-b"],
        }
    ]
    segments = {
        "seg-a": {"sequence_index": 1},
        "seg-b": {"sequence_index": 2},
    }

    source_storage = "workspaces/ws-1/sources/src-1/warfighting.pdf"
    file_info = executor._publish_artifact(
        workspace_id="ws-1",
        production_run_id="run-1",
        stage_run_id="sr-1",
        source={
            "id": "src-1",
            "filename": "warfighting.pdf",
            "storage_path": source_storage,
            "source_metadata": {},
        },
        chapters=chapters,
        segments=segments,
    )

    assert file_info is not None
    assert file_info["artifact_id"] == "art-1"
    assert file_info["filename"].endswith("-narration.json")
    assert file_info["storage_path"] == (
        "workspaces/ws-1/sources/src-1/artifacts/art-1/" + file_info["filename"]
    )
    assert storage.upload_buckets[file_info["storage_path"]] == "sources"

    created = db.created_artifacts[0]
    assert created["artifact_type"] == "narration_audio"
    assert created["format"] == "json"
    assert created["manifest"]["segment_count"] == 2
    assert created["manifest"]["chapter_titles"] == ["Chapter One"]

    body = storage.uploads[file_info["storage_path"]]
    assert storage.upload_content_types[file_info["storage_path"]] == "application/json"
    manifest = json.loads(body.decode("utf-8"))
    assert manifest["voice_id"] == "voice-1"
    assert manifest["total_duration_seconds"] == 5.5
    assert manifest["segment_count"] == 2
    first = manifest["chapters"][0]["segments"][0]
    assert first["segment_id"] == "seg-a"
    assert first["audio_path"] == "workspaces/ws-1/sources/src-1/narration/v/seg-a.mp3"
    assert first["words"][0]["w"] == "Hello"
    assert "file" not in first


def test_publish_artifact_none_when_no_narration() -> None:
    from app.worker.narration_executor import NarrationStageExecutor

    executor = NarrationStageExecutor(
        db=_FakeWorkerDb([]),  # type: ignore[arg-type]
        storage=_FakeWorkerStorage(),  # type: ignore[arg-type]
        client=ElevenLabsClient(api_key="k", voice_id="v", model_id="eleven_v3"),
        max_segment_chars=9500,
    )
    assert (
        executor._publish_artifact(
            workspace_id="ws-1",
            production_run_id="run-1",
            stage_run_id="sr-1",
            source={"id": "src-1", "filename": "x.pdf", "source_metadata": {}},
            chapters=[],
            segments={},
        )
        is None
    )
