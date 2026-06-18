from __future__ import annotations

from typing import Any


def _source_metadata(source: dict[str, Any]) -> dict[str, Any]:
    metadata = source.get("source_metadata") or {}
    return metadata if isinstance(metadata, dict) else {}


def source_parse_complete(source: dict[str, Any]) -> bool:
    parse_meta = _source_metadata(source).get("parse")
    return isinstance(parse_meta, dict) and bool(parse_meta.get("parsed_at"))


def source_research_complete(source: dict[str, Any]) -> bool:
    research = _source_metadata(source).get("research")
    return isinstance(research, dict) and bool(research.get("researched_at"))


def source_prepare_complete(source: dict[str, Any]) -> bool:
    prepare = _source_metadata(source).get("prepare")
    return isinstance(prepare, dict) and bool(prepare.get("prepared_at"))


def source_chunk_complete(source: dict[str, Any], *, has_segments: bool) -> bool:
    if not has_segments:
        return False

    parse_meta = _source_metadata(source).get("parse")
    return isinstance(parse_meta, dict) and bool(parse_meta.get("chunked_at"))


def source_deconstruct_complete(
    source: dict[str, Any],
    *,
    has_document_chapters: bool,
    has_completed_skill_run: bool,
) -> bool:
    deconstruct = _source_metadata(source).get("deconstruct")
    if isinstance(deconstruct, dict):
        if deconstruct.get("deconstructed_at") and deconstruct.get("chapter_count", 0) > 0:
            return True

    return has_document_chapters or has_completed_skill_run


def source_extract_complete(
    source: dict[str, Any],
    *,
    has_completed_skill_run: bool,
) -> bool:
    extract = _source_metadata(source).get("extract")
    if isinstance(extract, dict) and extract.get("extracted_at"):
        return True

    return has_completed_skill_run


def source_intellex_complete(
    source: dict[str, Any],
    *,
    has_segments: bool,
    has_document_chapters: bool,
    has_deconstruct_skill_run: bool,
    has_extract_skill_run: bool,
) -> bool:
    return (
        bool(source.get("storage_path"))
        and source_parse_complete(source)
        and source_research_complete(source)
        and source_prepare_complete(source)
        and source_chunk_complete(source, has_segments=has_segments)
        and source_deconstruct_complete(
            source,
            has_document_chapters=has_document_chapters,
            has_completed_skill_run=has_deconstruct_skill_run,
        )
        and source_extract_complete(
            source,
            has_completed_skill_run=has_extract_skill_run,
        )
    )
