from app.intellex.source_readiness import source_intellex_complete


def _ready_source(*, with_extract_metadata: bool = True) -> dict:
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
            "chapter_count": 4,
        },
        "validate": {
            "validated_at": "2026-06-08T00:00:04+00:00",
            "valid": True,
        },
    }

    if with_extract_metadata:
        metadata["extract"] = {
            "extracted_at": "2026-06-08T00:00:07+00:00",
            "chapter_count": 4,
            "item_counts": {"term": 2, "concept": 4, "insight": 1},
        }

    return {
        "id": "src-1",
        "storage_path": "workspaces/ws/sources/src-1/file.pdf",
        "status": "ready",
        "source_metadata": metadata,
    }


def test_source_intellex_complete_when_all_metadata_present() -> None:
    assert source_intellex_complete(
        _ready_source(),
        has_segments=True,
        has_document_chapters=False,
        has_structure_stage_run=False,
        has_extract_stage_run=False,
    )


def test_source_intellex_complete_without_extract_metadata_uses_stage_run() -> None:
    assert source_intellex_complete(
        _ready_source(with_extract_metadata=False),
        has_segments=True,
        has_document_chapters=True,
        has_structure_stage_run=True,
        has_extract_stage_run=True,
    )


def test_source_intellex_complete_requires_extract() -> None:
    assert not source_intellex_complete(
        _ready_source(with_extract_metadata=False),
        has_segments=True,
        has_document_chapters=True,
        has_structure_stage_run=True,
        has_extract_stage_run=False,
    )


def test_source_intellex_complete_requires_segments() -> None:
    assert not source_intellex_complete(
        _ready_source(),
        has_segments=False,
        has_document_chapters=True,
        has_structure_stage_run=True,
        has_extract_stage_run=True,
    )


def test_source_intellex_complete_requires_normalize() -> None:
    source = _ready_source()
    source["source_metadata"].pop("normalize")

    assert not source_intellex_complete(
        source,
        has_segments=True,
        has_document_chapters=True,
        has_structure_stage_run=True,
        has_extract_stage_run=True,
    )


def test_source_intellex_complete_requires_trim() -> None:
    source = _ready_source()
    source["source_metadata"].pop("trim")

    assert not source_intellex_complete(
        source,
        has_segments=True,
        has_document_chapters=True,
        has_structure_stage_run=True,
        has_extract_stage_run=True,
    )


def test_source_intellex_complete_requires_validate() -> None:
    source = _ready_source()
    source["source_metadata"].pop("validate")

    assert not source_intellex_complete(
        source,
        has_segments=True,
        has_document_chapters=True,
        has_structure_stage_run=True,
        has_extract_stage_run=True,
    )


def test_source_structure_falls_back_to_stage_run_without_metadata() -> None:
    source = _ready_source()
    source["source_metadata"].pop("structure")

    assert source_intellex_complete(
        source,
        has_segments=True,
        has_document_chapters=True,
        has_structure_stage_run=True,
        has_extract_stage_run=True,
    )
