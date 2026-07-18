"""Backfill document_chapters.sections for rows ingested before migration 32.

Derives sections from the heading segments the same way chunk.py now does:
within a chapter's ordered segment_ids, the first heading is the chapter title;
every subsequent heading starts a level-2 section that runs until the next
heading. Only rows with empty sections are touched, so this is idempotent and
safe to re-run.

    python -m scripts.backfill_chapter_sections
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.config import get_settings
from app.services.supabase_rest import SupabaseRestClient

BATCH = 500


def derive_sections(
    segment_ids: list[str],
    seg_map: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    seen_title = False

    for sid in segment_ids:
        seg = seg_map.get(sid)
        if seg is None:
            continue
        if seg["kind"] == "heading":
            if not seen_title:
                seen_title = True  # the chapter title heading
                continue
            current = {
                "title": seg["text"],
                "level": 2,
                "sequence_index": seg["sequence_index"],
                "heading_segment_id": sid,
                "segment_ids": [sid],
            }
            sections.append(current)
        elif current is not None:
            current["segment_ids"].append(sid)

    return sections


async def _segments_for_source(db: SupabaseRestClient, source_id: str) -> dict[str, dict[str, Any]]:
    seg_map: dict[str, dict[str, Any]] = {}
    offset = 0
    while True:
        rows = await db.select_many(
            "ndr_segments",
            filters={"source_id": f"eq.{source_id}"},
            columns="id,kind,text,sequence_index",
            order="sequence_index.asc",
            limit=1000,
            offset=offset,
        )
        if not rows:
            break
        for row in rows:
            seg_map[row["id"]] = row
        offset += len(rows)
    return seg_map


async def main() -> None:
    db = SupabaseRestClient(get_settings())
    updated = 0
    seg_cache: dict[str, dict[str, dict[str, Any]]] = {}
    offset = 0

    while True:
        chapters = await db.select_many(
            "document_chapters",
            order="source_id.asc",
            limit=BATCH,
            offset=offset,
        )
        if not chapters:
            break
        offset += len(chapters)

        for chapter in chapters:
            if chapter.get("sections"):
                continue  # already populated
            source_id = chapter["source_id"]
            if source_id not in seg_cache:
                seg_cache[source_id] = await _segments_for_source(db, source_id)

            sections = derive_sections(chapter.get("segment_ids") or [], seg_cache[source_id])
            if not sections:
                continue

            await db.update(
                "document_chapters",
                filters={"id": f"eq.{chapter['id']}"},
                payload={"sections": sections},
            )
            updated += 1
            print(f"  chapter {chapter['id']}: {len(sections)} sections")

    print(f"Done: populated sections on {updated} chapter(s).")


if __name__ == "__main__":
    asyncio.run(main())
