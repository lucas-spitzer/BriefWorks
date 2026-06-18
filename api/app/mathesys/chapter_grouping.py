from __future__ import annotations

from typing import Any


def _segment_page(segment: dict[str, Any]) -> int | None:
    locator = segment.get("locator") or {}
    page = locator.get("page")

    if isinstance(page, int):
        return page

    return None


def chapter_page_count(chapter: dict[str, Any]) -> int:
    pages = {
        page
        for segment in chapter.get("segments", [])
        if (page := _segment_page(segment)) is not None
    }

    return len(pages) if pages else 1


def group_segments_into_chapters(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not segments:
        return []

    chapters: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for segment in segments:
        is_heading = segment.get("kind") == "heading"

        if is_heading and current and current.get("segments"):
            chapters.append(current)
            current = {
                "title": str(segment.get("text") or "Untitled Section"),
                "segments": [segment],
            }
            continue

        if is_heading and not current:
            current = {
                "title": str(segment.get("text") or "Untitled Section"),
                "segments": [segment],
            }
            continue

        if current is None:
            current = {
                "title": "Introduction",
                "segments": [segment],
            }
            continue

        current["segments"].append(segment)

    if current:
        chapters.append(current)

    return chapters


def hydrate_chapters_from_rows(
    chapter_rows: list[dict[str, Any]],
    segment_index: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    chapters: list[dict[str, Any]] = []

    for row in chapter_rows:
        segments = [
            segment_index[str(segment_id)]
            for segment_id in (row.get("segment_ids") or [])
            if str(segment_id) in segment_index
        ]

        if not segments:
            continue

        chapters.append(
            {
                "title": str(row.get("title") or "Untitled Section"),
                "segments": segments,
            },
        )

    return chapters


def resolve_chapters_for_source(
    *,
    chapter_rows: list[dict[str, Any]],
    segments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if chapter_rows:
        segment_index = {str(segment["id"]): segment for segment in segments}
        hydrated = hydrate_chapters_from_rows(chapter_rows, segment_index)
        if hydrated:
            return hydrated

    return group_segments_into_chapters(segments)


def split_chapters_into_volumes(
    chapters: list[dict[str, Any]],
    *,
    max_pages: int = 500,
) -> list[list[dict[str, Any]]]:
    if not chapters:
        return []

    volumes: list[list[dict[str, Any]]] = []
    current_volume: list[dict[str, Any]] = []
    current_pages = 0

    for chapter in chapters:
        chapter_pages = chapter_page_count(chapter)

        if current_volume and current_pages + chapter_pages > max_pages:
            volumes.append(current_volume)
            current_volume = [chapter]
            current_pages = chapter_pages
            continue

        current_volume.append(chapter)
        current_pages += chapter_pages

    if current_volume:
        volumes.append(current_volume)

    return volumes
