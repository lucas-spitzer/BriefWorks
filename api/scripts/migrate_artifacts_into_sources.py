"""Retired. Artifacts now live at `{workspace_slug}/{source_slug}/book.epub`.

Use `python -m scripts.migrate_library_slugs` for the slug layout.
"""

New layout (sibling of parse/structure/narration under each source):

    workspaces/{ws}/sources/{source_id}/artifacts/{type}/{artifact_id}/{filename}

Old layout (separate bucket):

    workspaces/{ws}/artifacts/{artifact_id}/{filename}   # bucket: artifacts

Safe to re-run: rows whose storage_path already sits under a source's
`artifacts/` folder are skipped. Old objects are left in place until you
confirm downloads, then purge the legacy bucket via the Storage API
(SQL deletes on storage.* are blocked by Supabase):

    python -m scripts.migrate_artifacts_into_sources
    python -m scripts.migrate_artifacts_into_sources --dry-run
    python -m scripts.migrate_artifacts_into_sources --purge-legacy-bucket

To nest already-colocated `artifacts/{uuid}/` files under type folders, use
`python -m scripts.nest_artifacts_by_type`.
"""

from __future__ import annotations

import argparse

from app.artifact_paths import downloadable_artifact_path
from app.config import get_settings
from app.services.supabase_rest import SupabaseRestClient
from app.worker.storage import WorkerStorage

LEGACY_ARTIFACTS_BUCKET = "artifacts"
BATCH = 100


def _is_already_colocated(storage_path: str) -> bool:
    """True when path is under .../sources/{id}/artifacts/... (sources bucket).

    Covers both the older `artifacts/{artifact_id}/` layout and the current
    `artifacts/{type}/{artifact_id}/` layout. Type nesting is a separate hop
    (`python -m scripts.nest_artifacts_by_type`).
    """
    parts = storage_path.split("/")
    try:
        sources_idx = parts.index("sources")
    except ValueError:
        return False
    return (
        sources_idx + 2 < len(parts)
        and parts[sources_idx + 2] == "artifacts"
    )


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

            if not old_path or old_path == "pending":
                print(f"  skip {artifact_id}: pending or empty path")
                continue
            if not source_id:
                print(f"  skip {artifact_id}: no source_id")
                continue
            if _is_already_colocated(old_path):
                print(f"  skip {artifact_id}: already colocated")
                continue

            source = await db.select_one(
                "sources", filters={"id": f"eq.{source_id}"}
            )
            if not source or not source.get("storage_path"):
                print(f"  skip {artifact_id}: source {source_id} missing storage_path")
                continue

            leaf = filename or old_path.rsplit("/", 1)[-1]
            artifact_type = str(row.get("artifact_type") or "")
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
            content_type = _content_type(filename, row.get("format"))

            print(f"  {artifact_id}: {old_path} -> {new_path}")
            if dry_run:
                moved += 1
                continue

            blob = storage.download(old_path, bucket=LEGACY_ARTIFACTS_BUCKET)
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


def purge_legacy_bucket(*, dry_run: bool) -> None:
    """Empty and delete the legacy artifacts bucket via the Storage API."""
    storage = WorkerStorage()
    print(
        f"Purging legacy bucket {LEGACY_ARTIFACTS_BUCKET!r}"
        + (" (dry-run)" if dry_run else "")
        + "..."
    )
    if dry_run:
        print("  would empty + delete bucket via Storage API")
        return
    storage.empty_bucket(LEGACY_ARTIFACTS_BUCKET)
    print("  emptied")
    storage.delete_bucket(LEGACY_ARTIFACTS_BUCKET)
    print("  deleted")


async def main_async(*, dry_run: bool, purge: bool) -> None:
    if purge:
        purge_legacy_bucket(dry_run=dry_run)
        print("Done.")
        return

    print(
        "Migrating artifacts into sources bucket"
        + (" (dry-run)" if dry_run else "")
        + "..."
    )
    count = await migrate(dry_run=dry_run)
    print(f"Done: {count} artifact(s) {'would move' if dry_run else 'moved'}.")


def main() -> None:
    import asyncio

    parser = argparse.ArgumentParser(
        description="Colocate artifact files under each source in the sources bucket.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned moves without copying or updating rows.",
    )
    parser.add_argument(
        "--purge-legacy-bucket",
        action="store_true",
        help=(
            "Empty and delete the legacy artifacts storage bucket via the "
            "Storage API (run after migrate + download checks). "
            "Do not use SQL deletes on storage.*."
        ),
    )
    args = parser.parse_args()
    asyncio.run(
        main_async(dry_run=args.dry_run, purge=args.purge_legacy_bucket)
    )


if __name__ == "__main__":
    main()
