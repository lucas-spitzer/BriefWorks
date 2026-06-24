#!/usr/bin/env python3
"""Re-run extract-knowledge for existing sources (objectives + quote spans upgrade)."""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

API_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_DIR))

from app.intellex.stages.extract_chapter_knowledge import ExtractChapterKnowledgeStage
from app.intellex.stages.wiki_promotion import promote_concepts_to_wiki, resolve_prerequisites
from app.worker.db import WorkerDatabase


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _clear_extract_namespace(source_metadata: dict[str, Any]) -> dict[str, Any]:
    updated = dict(source_metadata)
    updated.pop("extract", None)
    return updated


def reextract_source(
    db: WorkerDatabase,
    source: dict[str, Any],
    *,
    dry_run: bool,
) -> dict[str, Any]:
    source_id = source["id"]
    workspace_id = source["workspace_id"]
    source_metadata = source.get("source_metadata") or {}

    if not isinstance(source_metadata, dict):
        source_metadata = {}

    segments = db.list_ndr_segments_for_source(source_id)
    chapter_rows = db.list_document_chapters_for_source(source_id)

    if not segments:
        raise RuntimeError(f"No NDR segments found for source {source_id}.")
    if not chapter_rows:
        raise RuntimeError(f"No document chapters found for source {source_id}.")

    if dry_run:
        return {
            "source_id": source_id,
            "chapter_count": len(chapter_rows),
            "segment_count": len(segments),
            "dry_run": True,
        }

    cleared_metadata = _clear_extract_namespace(source_metadata)
    db.update_source(source_id, {"source_metadata": cleared_metadata})

    segment_index = {str(segment["id"]): segment for segment in segments}
    existing_entries = db.list_wiki_entries_for_workspace(workspace_id)
    existing_labels = [str(entry["preferred_label"]) for entry in existing_entries]

    stage = ExtractChapterKnowledgeStage()
    output, execution = stage.run(
        source_metadata=cleared_metadata,
        chapter_rows=chapter_rows,
        segments=segments,
        existing_labels=existing_labels,
    )

    inserts, updates, disputes = promote_concepts_to_wiki(
        workspace_id=workspace_id,
        source_id=source_id,
        stage_run_id=None,
        stage_id="extract-knowledge",
        stage_version="2.0",
        concepts=output.items,
        segment_index=segment_index,
        existing_entries=existing_entries,
    )

    created_rows = db.insert_wiki_entries(inserts)

    for update in updates:
        wiki_id = update.pop("id")
        db.update_wiki_entry(wiki_id, update)

    if disputes:
        db.insert_wiki_disputes(disputes)

    all_rows = db.list_wiki_entries_for_workspace(workspace_id)
    slug_to_row = {str(row["canonical_slug"]): row for row in all_rows}

    for row in created_rows:
        slug_to_row[str(row["canonical_slug"])] = row

    prerequisite_updates = resolve_prerequisites(
        concepts=output.items,
        wiki_rows=list(slug_to_row.values()),
    )

    for update in prerequisite_updates:
        wiki_id = update.pop("id")
        db.update_wiki_entry(wiki_id, update)

    item_counts = {
        "term": sum(1 for item in output.items if item.entry_kind == "term"),
        "concept": sum(1 for item in output.items if item.entry_kind == "concept"),
        "insight": sum(1 for item in output.items if item.entry_kind == "insight"),
    }

    updated_metadata = {
        **cleared_metadata,
        "extract": {
            "extracted_at": utc_now_iso(),
            "chapter_count": len(chapter_rows),
            "item_counts": item_counts,
            "objective_count": len(output.learning_objectives),
            "learning_objectives": [obj.model_dump() for obj in output.learning_objectives],
            "reextracted": True,
        },
    }
    db.update_source(source_id, {"source_metadata": updated_metadata})

    return {
        "source_id": source_id,
        "item_count": len(output.items),
        "objective_count": len(output.learning_objectives),
        "wiki_inserts": len(created_rows),
        "wiki_updates": len(updates),
        "disputes": len(disputes),
        "model": execution.get("model"),
        "provider": execution.get("provider"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-id", help="Re-extract knowledge for one source")
    parser.add_argument("--workspace-id", help="Re-extract knowledge for all sources in a workspace")
    parser.add_argument("--dry-run", action="store_true", help="Print planned work without calling LLM")
    args = parser.parse_args()

    if not args.source_id and not args.workspace_id:
        parser.error("Provide --source-id or --workspace-id")

    db = WorkerDatabase()

    if args.source_id:
        sources = db.get_sources([args.source_id])
    else:
        sources = db.list_sources_for_workspace(args.workspace_id)

    if not sources:
        print("No sources found.", file=sys.stderr)
        return 1

    for source in sources:
        try:
            result = reextract_source(db, source, dry_run=args.dry_run)
            if args.dry_run:
                print(
                    f"[dry-run] {result['source_id']}: "
                    f"{result['chapter_count']} chapters, {result['segment_count']} segments",
                )
            else:
                print(
                    f"Re-extracted {result['source_id']}: "
                    f"{result['item_count']} items, {result['objective_count']} objectives "
                    f"({result['wiki_inserts']} wiki inserts, {result['wiki_updates']} updates)",
                )
        except Exception as exc:
            print(f"Failed {source['id']}: {exc}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
