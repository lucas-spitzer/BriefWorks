from app.intellex.source_readiness import (
    CURRENT_STRUCTURE_VERSION,
    source_intellex_complete,
    source_structure_complete,
)


def _ready_source() -> dict:
    metadata = {
        "parse": {
            "parsed_at": "2026-06-08T00:00:00+00:00",
            "chunked_at": "2026-06-08T00:00:05+00:00",
        },
        "research": {
            "researched_at": "2026-06-08T00:00:06+00:00",
        },
        "normalize": {
            "normalized_at": "2026-06-08T00:00:01+00:00",
        },
        "trim": {
            "trimmed_at": "2026-06-08T00:00:02+00:00",
        },
        "structure": {
            "structured_at": "2026-06-08T00:00:03+00:00",
            "stage_version": CURRENT_STRUCTURE_VERSION,
            "chapter_count": 4,
        },
        "validate": {
            "validated_at": "2026-06-08T00:00:04+00:00",
            "valid": True,
        },
    }

    return {
        "id": "src-1",
        "storage_path": "workspaces/ws/sources/src-1/file.pdf",
        "status": "ready",
        "source_metadata": metadata,
    }


def test_source_intellex_complete_when_all_metadata_present() -> None:
    assert source_intellex_complete(_ready_source(), has_segments=True)


def test_source_intellex_complete_does_not_require_extraction() -> None:
    # Knowledge extraction was removed from ingest: a source with no extract
    # metadata and no extract stage run is still intellex-complete.
    source = _ready_source()
    assert "extract" not in source["source_metadata"]

    assert source_intellex_complete(source, has_segments=True)


def test_source_intellex_complete_requires_segments() -> None:
    assert not source_intellex_complete(_ready_source(), has_segments=False)


def test_source_intellex_complete_requires_normalize() -> None:
    source = _ready_source()
    source["source_metadata"].pop("normalize")

    assert not source_intellex_complete(source, has_segments=True)


def test_source_intellex_complete_requires_trim() -> None:
    source = _ready_source()
    source["source_metadata"].pop("trim")

    assert not source_intellex_complete(source, has_segments=True)


def test_source_intellex_complete_requires_validate() -> None:
    source = _ready_source()
    source["source_metadata"].pop("validate")

    assert not source_intellex_complete(source, has_segments=True)


def test_source_structure_requires_current_stage_version() -> None:
    source = _ready_source()
    source["source_metadata"]["structure"]["stage_version"] = "1.1"

    assert not source_structure_complete(source)
    assert not source_intellex_complete(source, has_segments=True)


def test_source_structure_missing_stage_version_is_stale() -> None:
    source = _ready_source()
    source["source_metadata"]["structure"].pop("stage_version")

    assert not source_structure_complete(source)


def test_source_structure_without_metadata_is_stale() -> None:
    source = _ready_source()
    source["source_metadata"].pop("structure")

    assert not source_structure_complete(source)
    assert not source_intellex_complete(source, has_segments=True)
