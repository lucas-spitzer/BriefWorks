"""Copy live UUID library objects onto slug keys, then retarget Postgres.

    python -m scripts.migrate_library_slugs --dry-run
    python -m scripts.migrate_library_slugs
    python -m scripts.migrate_library_slugs --purge-old
"""

from __future__ import annotations

import argparse

from app.artifact_paths import (
    OUTPUT_FILENAMES,
    WORK_BOOK,
    WORK_NORMALIZED,
    WORK_PAGES,
    WORK_PARSE,
    WORK_TRIMMED,
    audio_clip_path,
    original_path,
    work_path,
)
from app.config import get_settings
from app.services.supabase_rest import SupabaseRestClient
from app.worker.storage import WorkerStorage

WORKSPACE_ID = "539346a7-c82e-4f14-a5a5-919303f0a88b"
WORKSPACE_SLUG = "marine-corps-doctrine"
OLD_ROOT = f"workspaces/{WORKSPACE_ID}"

SOURCES = (
    {
        "id": "ef90337a-671a-475b-97b5-da257f7386b0",
        "slug": "mcdp-1-warfighting",
        "filename": "MCDP 1 Warfighting.pdf",
        "ebook_old": (
            f"{OLD_ROOT}/sources/ef90337a-671a-475b-97b5-da257f7386b0/"
            "artifacts/warfighting.epub"
        ),
        "ebook_id": "994595bf-043d-4dbf-aa12-f615ce136059",
        "narration_old": None,
        "narration_id": None,
    },
    {
        "id": "7b87e650-be13-413c-bf7e-32f3db8b863b",
        "slug": "mcdp-1-3-tactics",
        "filename": "MCDP 1-3 Tactics.pdf",
        "ebook_old": (
            f"{OLD_ROOT}/sources/7b87e650-be13-413c-bf7e-32f3db8b863b/"
            "artifacts/4e6c5db4-08b1-4ac9-8554-20aa64594fe2/tactics.epub"
        ),
        "ebook_id": "4e6c5db4-08b1-4ac9-8554-20aa64594fe2",
        "narration_old": (
            f"{OLD_ROOT}/sources/7b87e650-be13-413c-bf7e-32f3db8b863b/"
            "artifacts/narration/8b19c485-dc41-4748-963f-8cc7d7c2fef9/"
            "tactics-narration.json"
        ),
        "narration_id": "8b19c485-dc41-4748-963f-8cc7d7c2fef9",
    },
)

WORK_FILES = (
    ("parse/raw.md", WORK_PARSE, "text/markdown"),
    ("parse/structured.json", WORK_PAGES, "application/json"),
    ("structure/normalized.json", WORK_NORMALIZED, "application/json"),
    ("structure/trimmed.json", WORK_TRIMMED, "application/json"),
    ("structure/book.json", WORK_BOOK, "application/json"),
)


def _old_source_dir(source_id: str) -> str:
    return f"{OLD_ROOT}/sources/{source_id}"


async def migrate(*, dry_run: bool, purge_old: bool) -> None:
    settings = get_settings()
    db = SupabaseRestClient(settings)
    storage = WorkerStorage()
    copied = 0
    skipped = 0

    for source in SOURCES:
        old_dir = _old_source_dir(source["id"])
        slug = source["slug"]
        original = original_path(WORKSPACE_SLUG, slug, source["filename"])
        old_original = f"{old_dir}/{source['filename']}"
        copied, skipped = _copy(
            storage, old_original, original, "application/pdf", dry_run, copied, skipped
        )

        for old_name, new_name, content_type in WORK_FILES:
            copied, skipped = _copy(
                storage,
                f"{old_dir}/{old_name}",
                work_path(WORKSPACE_SLUG, slug, new_name),
                content_type,
                dry_run,
                copied,
                skipped,
            )

        if source["ebook_old"]:
            copied, skipped = _copy(
                storage,
                source["ebook_old"],
                f"{WORKSPACE_SLUG}/{slug}/{OUTPUT_FILENAMES['electronic_book']}",
                "application/epub+zip",
                dry_run,
                copied,
                skipped,
            )
        if source["narration_old"]:
            copied, skipped = _copy(
                storage,
                source["narration_old"],
                f"{WORKSPACE_SLUG}/{slug}/{OUTPUT_FILENAMES['narration_audio']}",
                "application/json",
                dry_run,
                copied,
                skipped,
            )

        audio_rows = await db.select_many(
            "narration_segments",
            filters={"source_id": f"eq.{source['id']}"},
            columns="id,audio_path",
        )
        seen_audio: set[str] = set()
        for row in audio_rows:
            old_audio = str(row.get("audio_path") or "")
            if not old_audio or old_audio in seen_audio:
                continue
            seen_audio.add(old_audio)
            new_audio = _rewrite_audio_path(old_audio, source["id"], slug)
            if new_audio is None:
                print(f"  skip audio (unrecognized): {old_audio}")
                skipped += 1
                continue
            copied, skipped = _copy(
                storage,
                old_audio,
                new_audio,
                "audio/mpeg",
                dry_run,
                copied,
                skipped,
            )

        if dry_run:
            continue

        await _rewrite_source_row(db, source, original)
        if source["ebook_id"]:
            await db.update(
                "artifacts",
                filters={"id": f"eq.{source['ebook_id']}"},
                payload={
                    "filename": OUTPUT_FILENAMES["electronic_book"],
                    "storage_path": (
                        f"{WORKSPACE_SLUG}/{slug}/{OUTPUT_FILENAMES['electronic_book']}"
                    ),
                },
            )
        if source["narration_id"]:
            await db.update(
                "artifacts",
                filters={"id": f"eq.{source['narration_id']}"},
                payload={
                    "filename": OUTPUT_FILENAMES["narration_audio"],
                    "storage_path": (
                        f"{WORKSPACE_SLUG}/{slug}/{OUTPUT_FILENAMES['narration_audio']}"
                    ),
                },
            )
        for row in audio_rows:
            old_audio = str(row.get("audio_path") or "")
            new_audio = _rewrite_audio_path(old_audio, source["id"], slug)
            if not new_audio or new_audio == old_audio:
                continue
            await db.update(
                "narration_segments",
                filters={"id": f"eq.{row['id']}"},
                payload={"audio_path": new_audio},
            )

    print(f"copied={copied} skipped={skipped} dry_run={dry_run}")

    if purge_old and not dry_run:
        deleted = storage.delete_prefix(f"{OLD_ROOT}/")
        print(f"deleted {deleted} objects under {OLD_ROOT}/")


def _copy(
    storage: WorkerStorage,
    old_path: str,
    new_path: str,
    content_type: str,
    dry_run: bool,
    copied: int,
    skipped: int,
) -> tuple[int, int]:
    if dry_run:
        print(f"  copy {old_path} -> {new_path}")
        return copied + 1, skipped
    try:
        storage.copy(old_path, new_path, content_type=content_type)
    except RuntimeError as exc:
        if "404" in str(exc):
            print(f"  missing {old_path}")
            return copied, skipped + 1
        raise
    print(f"  copied {new_path}")
    return copied + 1, skipped


def _rewrite_audio_path(old_path: str, source_id: str, source_slug: str) -> str | None:
    marker = f"{OLD_ROOT}/sources/{source_id}/narration/"
    if not old_path.startswith(marker):
        if old_path.startswith(f"{WORKSPACE_SLUG}/{source_slug}/audio/"):
            return old_path
        return None
    rest = old_path[len(marker) :]
    voice_id, _, filename = rest.partition("/")
    if not voice_id or not filename:
        return None
    return audio_clip_path(WORKSPACE_SLUG, source_slug, voice_id, filename)


async def _rewrite_source_row(
    db: SupabaseRestClient,
    source: dict[str, str],
    original: str,
) -> None:
    row = await db.select_one("sources", filters={"id": f"eq.{source['id']}"})
    if not row:
        raise RuntimeError(f"Source {source['id']} not found")
    metadata = dict(row.get("source_metadata") or {})
    parse = dict(metadata.get("parse") or {})
    structure = dict(metadata.get("structure") or {})
    slug = source["slug"]
    parse["raw_markdown_path"] = work_path(WORKSPACE_SLUG, slug, WORK_PARSE)
    parse["structured_pages_path"] = work_path(WORKSPACE_SLUG, slug, WORK_PAGES)
    structure["book_path"] = work_path(WORKSPACE_SLUG, slug, WORK_BOOK)
    metadata["parse"] = parse
    metadata["structure"] = structure
    await db.update(
        "sources",
        filters={"id": f"eq.{source['id']}"},
        payload={"storage_path": original, "source_metadata": metadata},
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--purge-old", action="store_true")
    args = parser.parse_args()
    import asyncio

    asyncio.run(migrate(dry_run=args.dry_run, purge_old=args.purge_old))


if __name__ == "__main__":
    main()
