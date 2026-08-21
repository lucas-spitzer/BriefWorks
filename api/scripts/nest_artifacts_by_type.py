"""Nest colocated downloadable artifacts under type folders.

From:

    workspaces/{ws}/sources/{source_id}/artifacts/{artifact_id}/{filename}

To:

    workspaces/{ws}/sources/{source_id}/artifacts/{type}/{artifact_id}/{filename}

Type folders are `ebook`, `narration`, and `wiki`. Voice-id folders under
`artifacts/` (working Reader MP3 dumps) are skipped. Old objects are left in
place until you confirm downloads.

    python -m scripts.nest_artifacts_by_type
    python -m scripts.nest_artifacts_by_type --dry-run
"""

from __future__ import annotations

import argparse

from app.artifact_paths import (
    downloadable_artifact_path,
    is_type_nested_artifact_path,
    needs_type_nesting,
)
from app.config import get_settings
from app.services.supabase_rest import SupabaseRestClient
from app.worker.storage import WorkerStorage

BATCH = 100


def _content_type(filename: str, format_hint: str | None) -> str:
    lower = filename.lower()
    if lower.endswith(".epub"):
        return "application/epub+zip"
    if lower.endswith(".json") or (format_hint or "").lower() == "json":
        return "application/json"
    return "application/octet-stream"


async def migrate(*, dry_run: bool) -> int:
    settings = get_settings()
    db = SupabaseRestClient(settings)
    storage = WorkerStorage()
    sources_bucket = settings.sources_bucket
    moved = 0
    offset = 0

    while True:
        rows = await db.select_many(
            "artifacts",
            order="created_at.asc",
            limit=BATCH,
            offset=offset,
        )
        if not rows:
            break

        for row in rows:
            artifact_id = row["id"]
            old_path = str(row.get("storage_path") or "")
            source_id = row.get("source_id")
            filename = str(row.get("filename") or "")
            artifact_type = str(row.get("artifact_type") or "")

            if not old_path or old_path == "pending":
                print(f"  skip {artifact_id}: pending or empty path")
                continue
            if not source_id:
                print(f"  skip {artifact_id}: no source_id")
                continue
            if is_type_nested_artifact_path(old_path):
                print(f"  skip {artifact_id}: already type-nested")
                continue
            if not needs_type_nesting(old_path):
                print(f"  skip {artifact_id}: not a UUID artifact folder ({old_path})")
                continue

            old_folder = old_path.rsplit("/", 2)[-2]
            if old_folder != str(artifact_id):
                print(
                    f"  skip {artifact_id}: folder {old_folder} does not match artifact id"
                )
                continue

            source = await db.select_one(
                "sources", filters={"id": f"eq.{source_id}"}
            )
            if not source or not source.get("storage_path"):
                print(f"  skip {artifact_id}: source {source_id} missing storage_path")
                continue

            leaf = filename or old_path.rsplit("/", 1)[-1]
            try:
                new_path = downloadable_artifact_path(
                    str(source["storage_path"]),
                    artifact_type,
                    artifact_id,
                    leaf,
                )
            except ValueError:
                print(f"  skip {artifact_id}: unknown artifact_type {artifact_type!r}")
                continue

            if new_path == old_path:
                print(f"  skip {artifact_id}: path unchanged")
                continue

            content_type = _content_type(filename, row.get("format"))
            print(f"  {artifact_id}: {old_path} -> {new_path}")
            if dry_run:
                moved += 1
                continue

            blob = storage.download(old_path, bucket=sources_bucket)
            storage.upload(
                new_path,
                blob,
                bucket=sources_bucket,
                content_type=content_type,
                upsert=True,
            )
            await db.update(
                "artifacts",
                filters={"id": f"eq.{artifact_id}"},
                payload={"storage_path": new_path},
            )
            moved += 1

        if len(rows) < BATCH:
            break
        offset += BATCH

    return moved


async def main_async(*, dry_run: bool) -> None:
    print(
        "Nesting artifacts under type folders"
        + (" (dry-run)" if dry_run else "")
        + "..."
    )
    count = await migrate(dry_run=dry_run)
    print(f"Done: {count} artifact(s) {'would move' if dry_run else 'moved'}.")


def main() -> None:
    import asyncio

    parser = argparse.ArgumentParser(
        description=(
            "Copy colocated artifacts/{uuid}/ files into "
            "artifacts/{type}/{uuid}/ and update storage_path."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned moves without copying or updating rows.",
    )
    args = parser.parse_args()
    asyncio.run(main_async(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
