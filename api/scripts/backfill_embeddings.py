"""Backfill pgvector embeddings for the Reader assistant.

Embeds every ndr_segments / wiki_entries row that has no embedding yet and
writes the vector back. Safe to re-run — it only touches rows where
`embedded_at is null`.

    python -m scripts.backfill_embeddings              # both tables
    python -m scripts.backfill_embeddings --table wiki_entries

After the initial run, keep embeddings fresh by calling embed-on-write in the
ingest path (app/intellex/structuring/chunk.py) and on wiki authoring commit
(app/services/wiki_authoring.py).
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone

from app.config import get_settings
from app.services.embeddings import get_embedding_client, to_pgvector_literal
from app.services.supabase_rest import SupabaseRestClient

BATCH = 100
# preferred_label + definition gives the wiki vector more signal than either alone.
TEXT_BUILDERS = {
    "ndr_segments": lambda row: row.get("text", ""),
    "wiki_entries": lambda row: f"{row.get('preferred_label', '')}. {row.get('definition', '')}",
}


async def backfill_table(db: SupabaseRestClient, table: str) -> int:
    embed_client = get_embedding_client()
    build_text = TEXT_BUILDERS[table]
    total = 0

    while True:
        rows = await db.select_many(
            table,
            filters={"embedded_at": "is.null"},
            order="created_at.asc",
            limit=BATCH,
        )
        if not rows:
            break

        texts = [build_text(row) or " " for row in rows]
        vectors = embed_client.embed(texts)
        now = datetime.now(timezone.utc).isoformat()

        for row, vector in zip(rows, vectors):
            await db.update(
                table,
                filters={"id": f"eq.{row['id']}"},
                payload={"embedding": to_pgvector_literal(vector), "embedded_at": now},
            )

        total += len(rows)
        print(f"  {table}: embedded {total} rows...")

    return total


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--table", choices=list(TEXT_BUILDERS), default=None)
    args = parser.parse_args()

    db = SupabaseRestClient(get_settings())
    tables = [args.table] if args.table else list(TEXT_BUILDERS)
    for table in tables:
        print(f"Backfilling {table}...")
        count = await backfill_table(db, table)
        print(f"Done: {count} {table} rows embedded.")


if __name__ == "__main__":
    asyncio.run(main())
