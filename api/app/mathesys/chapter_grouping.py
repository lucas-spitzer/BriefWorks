from __future__ import annotations

from typing import Any

from app.intellex.heading_classification import (
    is_chapter_boundary_heading,
    parse_chapter_boundary_number,
)


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


def _refine_chapter_title(chapter: dict[str, Any]) -> dict[str, Any]:
    segments = chapter.get("segments") or []

    if len(segments) < 2:
        return chapter

    first = segments[0]
    second = segments[1]

    if first.get("kind") != "heading" or second.get("kind") != "heading":
        return chapter

    first_text = str(first.get("text") or "").strip()
    second_text = str(second.get("text") or "").strip()

    if is_chapter_boundary_heading(first_text) and not is_chapter_boundary_heading(second_text):
        return {
            **chapter,
            "title": f"{first_text} — {second_text}",
        }

    return chapter


def _looks_like_chapter_subtitle(opening: str) -> bool:
    if not opening:
        return False

    if opening[0] in {'"', "'", "“", "‘", "«"}:
        return False

    if opening.isupper() and any(character.isalpha() for character in opening):
        return False

    if "\n" in opening:
        return False

    return True


def _split_chapter_opening_remainder(
    segment: dict[str, Any],
    remainder: str,
) -> list[dict[str, Any]]:
    """Promote a chapter subtitle line after 'Chapter N' inside a paragraph block."""
    if not remainder.strip():
        return []

    if "\n\n" not in remainder:
        return [
            {
                **segment,
                "id": f"{segment['id']}-continued",
                "kind": "paragraph",
                "text": remainder.strip(),
            },
        ]

    opening, body = remainder.split("\n\n", 1)
    opening = opening.strip()
    body = body.strip()

    if "\n" in opening or not _looks_like_chapter_subtitle(opening):
        return [
            {
                **segment,
                "id": f"{segment['id']}-continued",
                "kind": "paragraph",
                "text": remainder.strip(),
            },
        ]

    segments: list[dict[str, Any]] = []

    if opening:
        segments.append(
            {
                **segment,
                "id": f"{segment['id']}-subtitle",
                "kind": "heading",
                "text": opening,
            },
        )

    if body:
        segments.append(
            {
                **segment,
                "id": f"{segment['id']}-continued",
                "kind": "paragraph",
                "text": body,
            },
        )

    return segments


def _expand_paragraph_segment(segment: dict[str, Any]) -> list[dict[str, Any]]:
    """Split paragraph blocks on internal chapter boundary lines (LlamaParse pattern)."""
    text = str(segment.get("text") or "")

    if segment.get("kind") != "paragraph" or not text.strip():
        return [segment]

    lines = text.split("\n")
    boundary_indices = [
        index
        for index, line in enumerate(lines)
        if is_chapter_boundary_heading(line.strip())
    ]

    if not boundary_indices:
        return [segment]

    expanded: list[dict[str, Any]] = []
    cursor = 0
    split_index = 0

    for boundary_index in boundary_indices:
        before = "\n".join(lines[cursor:boundary_index]).strip()

        if before:
            expanded.append(
                {
                    **segment,
                    "id": f"{segment['id']}-pre{split_index}",
                    "kind": "paragraph",
                    "text": before,
                },
            )
            split_index += 1

        heading_text = lines[boundary_index].strip()
        expanded.append(
            {
                **segment,
                "id": f"{segment['id']}-boundary{split_index}",
                "kind": "heading",
                "text": heading_text,
            },
        )
        split_index += 1
        cursor = boundary_index + 1

    remainder = "\n".join(lines[cursor:]).strip()

    if remainder:
        expanded.extend(
            _split_chapter_opening_remainder(
                {**segment, "id": f"{segment['id']}-post{split_index}"},
                remainder,
            ),
        )

    return expanded


def _expand_segments_for_chapter_boundaries(
    segments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Split paragraph blocks that contain chapter headings (common in LlamaParse)."""
    expanded: list[dict[str, Any]] = []

    for segment in segments:
        text = str(segment.get("text") or "").strip()

        if segment.get("kind") == "heading" and is_chapter_boundary_heading(text):
            expanded.append(segment)
            continue

        if segment.get("kind") == "paragraph":
            expanded.extend(_expand_paragraph_segment(segment))
            continue

        expanded.append(segment)

    return expanded


def _starts_new_chapter(
    title: str,
    *,
    expected_chapter_number: int,
) -> tuple[bool, int]:
    if not is_chapter_boundary_heading(title):
        return False, expected_chapter_number

    chapter_number = parse_chapter_boundary_number(title)

    if chapter_number is not None and chapter_number != expected_chapter_number:
        return False, expected_chapter_number

    next_expected = expected_chapter_number + 1 if chapter_number is not None else expected_chapter_number + 1

    return True, next_expected


def group_segments_into_chapters(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group segments into chapters, splitting only on chapter/part boundaries."""
    if not segments:
        return []

    expanded_segments = _expand_segments_for_chapter_boundaries(segments)
    chapters: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    pending_before_first: list[dict[str, Any]] = []
    expected_chapter_number = 1

    for segment in expanded_segments:
        text = str(segment.get("text") or "").strip()
        starts_chapter, expected_chapter_number = _starts_new_chapter(
            text,
            expected_chapter_number=expected_chapter_number,
        )

        if segment.get("kind") == "heading" and starts_chapter:
            if current and current.get("segments"):
                chapters.append(_refine_chapter_title(current))

            start_segments = [*pending_before_first, segment]
            pending_before_first = []
            current = {
                "title": text,
                "segments": start_segments,
            }
            continue

        if current is None:
            pending_before_first.append(segment)
            continue

        current["segments"].append(segment)

    if current:
        chapters.append(_refine_chapter_title(current))

    if not chapters and pending_before_first:
        chapters.append(
            {
                "title": "Untitled Section",
                "segments": pending_before_first,
            },
        )

    return chapters


def collapse_chapter_rows_for_spine(
    chapter_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Merge subsection rows into the preceding chapter/part boundary."""
    ordered = sorted(chapter_rows, key=lambda row: row.get("sequence_index", 0))
    collapsed: list[dict[str, Any]] = []
    expected_chapter_number = 1

    for row in ordered:
        title = str(row.get("title") or "Untitled Section")
        segment_ids = [str(segment_id) for segment_id in (row.get("segment_ids") or [])]
        starts_chapter, expected_chapter_number = _starts_new_chapter(
            title,
            expected_chapter_number=expected_chapter_number,
        )

        if not collapsed or starts_chapter:
            collapsed.append(
                {
                    "id": row.get("id"),
                    "title": title,
                    "sequence_index": row.get("sequence_index"),
                    "level": 1,
                    "segment_ids": list(segment_ids),
                },
            )
            continue

        parent = collapsed[-1]
        parent["segment_ids"].extend(segment_ids)

    for index, row in enumerate(collapsed):
        row["sequence_index"] = index

    return collapsed


def resolve_epub_chapters_from_segments(
    segments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build EPUB/narration chapters directly from ordered NDR segments."""
    return group_segments_into_chapters(segments)


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
    grouped = group_segments_into_chapters(segments)

    if grouped:
        return grouped

    if chapter_rows:
        segment_index = {str(segment["id"]): segment for segment in segments}
        spine_rows = collapse_chapter_rows_for_spine(chapter_rows)
        hydrated = hydrate_chapters_from_rows(spine_rows, segment_index)
        if hydrated:
            return hydrated

    return []


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
