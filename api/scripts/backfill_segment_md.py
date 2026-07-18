"""Backfill ndr_segments.md from each source's persisted structure/book.json.

The chunk step now stores a markdown-faithful copy (`md`) alongside the plain
segment text so the Reader can render inline emphasis. Sources structured
before migration 35 only have the plain text; their markdown still lives in
the structure artifact. This script replays build_segments_and_chapters'
ordering over book.json and writes `md` back by (source_id, sequence_index),
verifying the flattened markdown matches the stored text before touching a
row. Only null-md paragraph rows are updated, so it is idempotent.

    python -m scripts.backfill_segment_md
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from app.config import get_settings
from app.intellex.structuring.chunk import display_markdown, flatten_markdown
from app.intellex.structuring.models import Book, book_from_dict
from app.services.supabase_rest import SupabaseRestClient
from app.worker.storage import WorkerStorage

BATCH = 500


def paragraph_md_by_sequence(book: Book) -> dict[int, str]:
    """Sequence-indexed markdown for every emitted paragraph segment.

    Mirrors build_segments_and_chapters: heading, intro paragraphs, then per
    section a heading followed by its body paragraphs; empty paragraphs are
    skipped without consuming a sequence index.
    """
    out: dict[int, str] = {}
    seq = 0
    for chapter in book.chapters:
        seq += 1  # chapter title heading
        for para in chapter.intro:
            if not flatten_markdown(para.md):
                continue
            out[seq] = para.md
            seq += 1
        for section in chapter.sections:
            seq += 1  # section heading
            for para in section.body:
                if not flatten_markdown(para.md):
                    continue
                out[seq] = para.md
                seq += 1
    return out


async def backfill_source(
    db: SupabaseRestClient,
    storage: WorkerStorage,
    source: dict[str, Any],
) -> tuple[int, int]:
    """Return (updated, skipped_mismatch) for one source."""
    book_path = ((source.get("source_metadata") or {}).get("structure") or {}).get("book_path")
    if not book_path:
        return 0, 0

    blob = storage.download(book_path, bucket=storage.sources_bucket)
    book = book_from_dict(json.loads(blob))
    md_by_seq = paragraph_md_by_sequence(book)

    updated = 0
    mismatched = 0
    offset = 0
    while True:
        rows = await db.select_many(
            "ndr_segments",
            filters={
                "source_id": f"eq.{source['id']}",
                "kind": "eq.paragraph",
                "md": "is.null",
            },
            order="sequence_index.asc",
            limit=BATCH,
            offset=offset,
        )
        if not rows:
            break
        offset += len(rows)

        for row in rows:
            raw_md = md_by_seq.get(row["sequence_index"])
            if raw_md is None:
                continue
            if flatten_markdown(raw_md) != row["text"]:
                mismatched += 1
                continue
            md = display_markdown(raw_md)
            if md is None:
                continue  # markdown adds nothing over the plain text
            await db.update(
                "ndr_segments",
                filters={"id": f"eq.{row['id']}"},
                payload={"md": md},
            )
            updated += 1

        if len(rows) < BATCH:
            break

    return updated, mismatched


async def main() -> None:
    db = SupabaseRestClient(get_settings())
    storage = WorkerStorage()

    total_updated = 0
    total_mismatched = 0
    offset = 0
    while True:
        sources = await db.select_many(
            "sources",
            order="created_at.asc",
            limit=BATCH,
            offset=offset,
        )
        if not sources:
            break
        offset += len(sources)

        for source in sources:
            updated, mismatched = await backfill_source(db, storage, source)
            total_updated += updated
            total_mismatched += mismatched
            if updated or mismatched:
                print(f"{source['id']}: updated={updated} mismatched={mismatched}")

        if len(sources) < BATCH:
            break

    print(f"Done. Updated {total_updated} segments; {total_mismatched} text mismatches skipped.")


if __name__ == "__main__":
    asyncio.run(main())
