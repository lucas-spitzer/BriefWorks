"""Manual knowledge curation: notes → structured entries → reviewed wiki rows.

The lifecycle (docs/internal/plans/wiki-authoring-contract.md):

1. ``create_batch`` — paste notes → structuring LLM → enriched ``draft`` batch.
2. ``create_file_batch`` — upload note files → ``transcribing`` (RQ) →
   ``transcribed`` (author edits) → ``structure_batch`` → ``draft``.
3. ``update_batch`` — review edits; slugs/resolutions recomputed server-side.
4. ``commit_batch`` — re-validates against the *current* wiki (409 on drift),
   promotes included entries through the shared candidate promotion, resolves
   prerequisites, embeds every touched entry, and marks the batch committed.

The structuring model never writes to ``wiki_entries`` directly — every entry
passes through human review first.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any

from app.config import Settings, get_settings
from app.intellex.wiki_candidates import (
    WikiCandidate,
    candidate_slug,
    definitions_conflict,
    promote_candidates,
    resolve_prerequisites,
)
from app.models.wiki_ingest import (
    WikiIngestCreate,
    WikiIngestEntry,
    WikiIngestEvidence,
    WikiIngestSimilarEntry,
)
from app.repositories.retrieval import RetrievalRepository
from app.repositories.wiki_entries import WikiEntryRepository
from app.repositories.wiki_ingest_batches import WikiIngestBatchRepository
from app.services.api_pricing import cost_llm_usage
from app.services.embeddings import EmbeddingClient, get_embedding_client, to_pgvector_literal
from app.services.llm import get_llm_client
from app.services.llm.base import LLMClient
from app.services.queue import enqueue_wiki_ingest_transcription
from app.services.retrieval import build_reader_link
from app.services.supabase_storage import SupabaseStorageClient, SupabaseStorageError
from app.services.wiki_transcription import (
    ValidatedAttachment,
    WikiTranscriptionError,
    attachment_storage_path,
    validate_note_attachment,
)

_DISCARDABLE_STATUSES = frozenset(
    {"transcribing", "transcribed", "structuring", "draft", "failed"},
)

STRUCTURING_ACTION = "wiki_structuring"

# When evidence search is restricted to one chapter we over-fetch source-wide
# matches and filter client-side (the RPC has no segment filter), so the
# chapter can still fill top_k after filtering.
_CHAPTER_OVERFETCH = 4

STRUCTURING_SYSTEM_PROMPT = """You convert a reader's unstructured book notes into structured wiki entries.

The notes are terminology, concepts, and insights the reader wrote down while reading. Your only job is to FORMAT them — never to add knowledge.

Rules:
1. Split, don't summarize. Each atomic term/concept/insight becomes its own entry; compound notes are split.
2. Merge within the batch. Obvious restatements of the same item collapse into one entry (merge their aliases).
3. No invention. Definitions may only rephrase the reader's words — fix grammar and expand shorthand, never add facts the notes don't contain. If a term is named but not defined, use the best available fragment as the definition.
4. Insights keep the reader's voice. Light grammar cleanup only.
5. Classification: vocabulary with a compact definition → "term"; an idea/model/framework → "concept"; a judgment/takeaway/lesson → "insight".
6. importance defaults to "supporting". Use "essential" or "contextual" only when the notes signal it ("key idea", "(minor)", emphasis). Do not inflate importance.
7. aliases: alternate names present in the notes ("aka …", parentheticals, abbreviations).
8. prerequisite_labels: only when the notes explicitly relate entries ("related to X", "builds on Y") — use the other entry's label.
9. pronunciation: only when the notes give one.
10. note_excerpt: a verbatim fragment (max 240 chars) of the notes this entry came from.
11. Anything you cannot confidently structure goes into unparsed_fragments verbatim — never guess it into an entry, never silently drop it.

Respond with a JSON object:
{
  "entries": [
    {
      "label": string,
      "entry_kind": "term" | "concept" | "insight",
      "definition": string,
      "aliases": [string],
      "pronunciation": string | null,
      "importance": "essential" | "supporting" | "contextual",
      "prerequisite_labels": [string],
      "note_excerpt": string
    }
  ],
  "unparsed_fragments": [string]
}"""


class WikiAuthoringError(Exception):
    """Invalid input or state; routers map this to 400."""


class WikiIngestNotFoundError(Exception):
    """Batch does not exist in this workspace; routers map this to 404."""


class WikiIngestDriftError(Exception):
    """Commit-time review state drifted against the current wiki (409)."""

    def __init__(self, drifted_indexes: list[int], batch: dict[str, Any]) -> None:
        super().__init__(
            "The wiki changed since this batch was reviewed. "
            "Re-confirm the highlighted entries and commit again.",
        )
        self.drifted_indexes = drifted_indexes
        self.batch = batch


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _embedding_text(label: str, definition: str) -> str:
    # Same shape as scripts/backfill_embeddings.py so every wiki vector lives
    # in one consistent space.
    return f"{label}. {definition}"


class WikiAuthoringService:
    def __init__(
        self,
        *,
        wiki_entries: WikiEntryRepository,
        batches: WikiIngestBatchRepository,
        retrieval: RetrievalRepository,
        settings: Settings | None = None,
        embedding_client: EmbeddingClient | None = None,
        llm_client: LLMClient | None = None,
        storage: SupabaseStorageClient | None = None,
    ) -> None:
        self.wiki_entries = wiki_entries
        self.batches = batches
        self.retrieval = retrieval
        self.settings = settings or get_settings()
        self._embedding_client = embedding_client
        self._llm_client = llm_client
        self._storage = storage

    @property
    def embedding_client(self) -> EmbeddingClient:
        if self._embedding_client is None:
            self._embedding_client = get_embedding_client()
        return self._embedding_client

    @property
    def llm_client(self) -> LLMClient:
        if self._llm_client is None:
            self._llm_client = get_llm_client(STRUCTURING_ACTION)
        return self._llm_client

    @property
    def storage(self) -> SupabaseStorageClient:
        if self._storage is None:
            self._storage = SupabaseStorageClient(self.settings)
        return self._storage

    # ------------------------------------------------------------------
    # Batch lifecycle
    # ------------------------------------------------------------------

    async def create_batch(
        self,
        payload: WikiIngestCreate,
        workspace_id: str,
    ) -> dict[str, Any]:
        notes = payload.notes.strip()

        if not notes:
            raise WikiAuthoringError("Notes are empty.")

        max_chars = self.settings.wiki_authoring.max_notes_chars
        if len(notes) > max_chars:
            raise WikiAuthoringError(
                f"Notes exceed {max_chars} characters. "
                "Split the dump (one chapter per batch works well).",
            )

        chapter = await self._resolve_chapter(payload.chapter_hint, payload.source_id)

        structured, model, cost_usd = await self._structure_notes(
            notes,
            chapter_title=(chapter or {}).get("title"),
        )

        entries = await self._enrich_entries(
            structured["entries"],
            workspace_id=workspace_id,
            source_id=payload.source_id,
            chapter=chapter,
        )

        title = (payload.title or "").strip() or f"Notes — {_utc_now_iso()[:10]}"
        row = await self.batches.insert(
            {
                "workspace_id": workspace_id,
                "source_id": payload.source_id,
                "title": title,
                "raw_notes": notes,
                "chapter_hint": payload.chapter_hint,
                "chapter": chapter,
                "status": "draft",
                "entries": [entry.model_dump() for entry in entries],
                "unparsed_fragments": structured["unparsed_fragments"],
                "attachments": [],
                "model": model,
                "cost_usd": cost_usd,
            },
        )
        return row

    async def create_file_batch(
        self,
        *,
        workspace_id: str,
        source_id: str,
        chapter_hint: str | None,
        title: str | None,
        files: list[tuple[str, str | None, bytes]],
    ) -> dict[str, Any]:
        """Create a ``transcribing`` batch from note uploads and enqueue RQ.

        ``files`` is ``(filename, content_type, content)`` in upload order.
        """
        if not (source_id or "").strip():
            raise WikiAuthoringError("source_id is required for file ingest.")

        wiki_settings = self.settings.wiki_authoring
        if not files:
            raise WikiAuthoringError("Upload at least one note file.")

        if len(files) > wiki_settings.max_attachments_per_batch:
            raise WikiAuthoringError(
                f"At most {wiki_settings.max_attachments_per_batch} files per batch.",
            )

        if not await self.batches.source_has_segments(source_id):
            raise WikiAuthoringError(
                "Selected source has no parsed segments yet. "
                "Finish ingesting the source before attaching reading notes.",
            )

        validated: list[ValidatedAttachment] = []
        try:
            for order, (filename, content_type, content) in enumerate(files):
                validated.append(
                    validate_note_attachment(
                        order=order,
                        filename=filename,
                        content_type=content_type,
                        content=content,
                        max_bytes=wiki_settings.max_attachment_bytes,
                    ),
                )
        except WikiTranscriptionError as exc:
            raise WikiAuthoringError(str(exc)) from exc

        chapter = await self._resolve_chapter(chapter_hint, source_id)
        batch_id = str(uuid.uuid4())
        attachments: list[dict[str, Any]] = []
        bucket = self.settings.sources_bucket

        try:
            for item in validated:
                path = attachment_storage_path(
                    workspace_id=workspace_id,
                    batch_id=batch_id,
                    order=item.order,
                    filename=item.filename,
                )
                await self.storage.upload(
                    bucket=bucket,
                    path=path,
                    content=item.content,
                    content_type=item.mime_type,
                )
                attachments.append(
                    {
                        "order": item.order,
                        "filename": item.filename,
                        "mime_type": item.mime_type,
                        "storage_path": path,
                        "byte_size": len(item.content),
                    },
                )
        except SupabaseStorageError as exc:
            raise WikiAuthoringError(f"Could not store note files: {exc}") from exc

        display_title = (title or "").strip() or f"Notes — {_utc_now_iso()[:10]}"
        row = await self.batches.insert(
            {
                "id": batch_id,
                "workspace_id": workspace_id,
                "source_id": source_id,
                "title": display_title,
                "raw_notes": "",
                "chapter_hint": chapter_hint,
                "chapter": chapter,
                "status": "transcribing",
                "entries": [],
                "unparsed_fragments": [],
                "attachments": attachments,
                "transcription_error": None,
            },
        )

        try:
            enqueue_wiki_ingest_transcription(self.settings, batch_id)
        except Exception as exc:  # noqa: BLE001 - surface queue failures to the API
            await self.batches.update(
                batch_id,
                {
                    "status": "failed",
                    "transcription_error": f"Failed to enqueue transcription: {exc}",
                },
            )
            raise WikiAuthoringError(
                f"Failed to enqueue transcription job: {exc}",
            ) from exc

        return row

    async def structure_batch(
        self,
        batch_id: str,
        workspace_id: str,
    ) -> dict[str, Any]:
        """Structure current ``raw_notes`` after transcription review."""
        batch = await self._require_batch(
            batch_id,
            workspace_id,
            allowed={"transcribed"},
        )
        notes = str(batch.get("raw_notes") or "").strip()

        if not notes:
            raise WikiAuthoringError("Notes are empty. Edit the transcription first.")

        max_chars = self.settings.wiki_authoring.max_notes_chars
        if len(notes) > max_chars:
            raise WikiAuthoringError(
                f"Notes exceed {max_chars} characters. "
                "Split into another batch (same source/chapter works well).",
            )

        await self.batches.update(
            batch_id,
            {"status": "structuring", "transcription_error": None},
        )

        chapter = batch.get("chapter")
        if not isinstance(chapter, dict):
            chapter = await self._resolve_chapter(
                batch.get("chapter_hint"),
                batch.get("source_id"),
            )

        try:
            structured, model, cost_usd = await self._structure_notes(
                notes,
                chapter_title=(chapter or {}).get("title"),
            )
            entries = await self._enrich_entries(
                structured["entries"],
                workspace_id=workspace_id,
                source_id=batch.get("source_id"),
                chapter=chapter if isinstance(chapter, dict) else None,
            )
            return await self.batches.update(
                batch_id,
                {
                    "status": "draft",
                    "entries": [entry.model_dump() for entry in entries],
                    "unparsed_fragments": structured["unparsed_fragments"],
                    "model": model,
                    "cost_usd": cost_usd,
                    "chapter": chapter,
                },
            )
        except Exception:
            await self.batches.update(batch_id, {"status": "transcribed"})
            raise

    async def update_batch(
        self,
        batch_id: str,
        workspace_id: str,
        *,
        title: str | None = None,
        raw_notes: str | None = None,
        entries: list[WikiIngestEntry] | None = None,
    ) -> dict[str, Any]:
        batch = await self.batches.get_for_workspace(batch_id, workspace_id)

        if not batch:
            raise WikiIngestNotFoundError("Ingest batch not found.")

        status = batch.get("status")
        payload: dict[str, Any] = {}

        if title is not None and title.strip():
            if status not in {"transcribed", "draft", "failed"}:
                raise WikiAuthoringError(
                    f"Batch is {status}; title can only be edited while "
                    "transcribed, draft, or failed.",
                )
            payload["title"] = title.strip()

        if raw_notes is not None:
            if status not in {"transcribed", "failed"}:
                raise WikiAuthoringError(
                    f"Batch is {status}; raw_notes can only be edited while "
                    "transcribed (or after a failed transcription).",
                )
            stripped = raw_notes.strip()
            if not stripped:
                raise WikiAuthoringError("Notes are empty.")
            payload["raw_notes"] = stripped
            if status == "failed":
                payload["status"] = "transcribed"
                payload["transcription_error"] = None

        if entries is not None:
            if status != "draft":
                raise WikiAuthoringError(
                    f"Batch is {status}; only drafts can edit structured entries.",
                )
            existing_entries = await self._list_all_entries(workspace_id)
            refreshed = self._refresh_resolutions(entries, existing_entries)
            payload["entries"] = [entry.model_dump() for entry in refreshed]

        if not payload:
            return batch

        return await self.batches.update(batch_id, payload)

    async def discard_batch(self, batch_id: str, workspace_id: str) -> dict[str, Any]:
        batch = await self.batches.get_for_workspace(batch_id, workspace_id)

        if not batch:
            raise WikiIngestNotFoundError("Ingest batch not found.")

        if batch.get("status") not in _DISCARDABLE_STATUSES:
            raise WikiAuthoringError(
                f"Batch is {batch.get('status')}; it cannot be discarded.",
            )

        return await self.batches.update(batch_id, {"status": "discarded"})

    async def commit_batch(
        self,
        batch_id: str,
        workspace_id: str,
    ) -> tuple[dict[str, Any], list[str], list[str]]:
        batch = await self._require_batch(batch_id, workspace_id, allowed={"draft"})
        entries = [WikiIngestEntry.model_validate(entry) for entry in batch.get("entries") or []]
        included = [entry for entry in entries if entry.include]

        if not included:
            raise WikiAuthoringError("No entries are marked for inclusion.")

        existing_entries = await self._list_all_entries(workspace_id)

        # Another batch (or a manual edit) may have landed since review: any
        # included entry whose resolution silently changed must be re-confirmed
        # before it can overwrite state the author never saw.
        refreshed = self._refresh_resolutions(entries, existing_entries)
        drifted = [
            entry.index
            for original, entry in zip(entries, refreshed)
            if entry.include
            and (
                entry.resolution != original.resolution
                or entry.existing_entry_id != original.existing_entry_id
            )
        ]

        if drifted:
            updated = await self.batches.update(
                batch_id,
                {"entries": [entry.model_dump() for entry in refreshed]},
            )
            raise WikiIngestDriftError(drifted, updated)

        source_id = batch.get("source_id")
        chapter = batch.get("chapter") or {}
        candidates = [
            self._entry_to_candidate(entry, batch_id=batch_id, source_id=source_id, chapter=chapter)
            for entry in refreshed
            if entry.include
        ]

        inserts, updates, _ = promote_candidates(
            workspace_id=workspace_id,
            candidates=candidates,
            existing_entries=existing_entries,
            # Conflicts were shown side-by-side in review; the author's
            # reviewed definition is the dispute resolution.
            override_conflicts=True,
        )

        inserted_rows = await self.wiki_entries.insert_many(inserts) if inserts else []
        updated_ids: list[str] = []

        for update in updates:
            update_payload = dict(update)
            wiki_id = update_payload.pop("id")
            await self.wiki_entries.update(wiki_id, update_payload)
            updated_ids.append(str(wiki_id))

        all_rows = await self._list_all_entries(workspace_id)
        for prereq_update in resolve_prerequisites(candidates=candidates, wiki_rows=all_rows):
            prereq_payload = dict(prereq_update)
            wiki_id = prereq_payload.pop("id")
            await self.wiki_entries.update(wiki_id, prereq_payload)

        inserted_ids = [str(row["id"]) for row in inserted_rows]
        await self._embed_entries(inserted_ids + updated_ids)

        committed = await self.batches.update(
            batch_id,
            {
                "status": "committed",
                "committed_at": _utc_now_iso(),
                "committed_entry_ids": inserted_ids + updated_ids,
            },
        )
        return committed, inserted_ids, updated_ids

    # ------------------------------------------------------------------
    # Single-entry CRUD (quick add / edit without the LLM)
    # ------------------------------------------------------------------

    async def create_entry(
        self,
        workspace_id: str,
        *,
        preferred_label: str,
        definition: str,
        entry_kind: str,
        importance: str,
        aliases: list[str],
        pronunciation: str | None,
        origin: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        existing_entries = await self._list_all_entries(workspace_id)
        entry_origin = origin if isinstance(origin, dict) and origin.get("kind") else {"kind": "manual"}
        candidate = WikiCandidate(
            label=preferred_label.strip(),
            definition=definition.strip(),
            entry_kind=entry_kind,
            importance=importance,
            aliases=aliases,
            pronunciation=pronunciation,
            origin=entry_origin,
        )
        slug = candidate_slug(candidate, {
            str(entry["canonical_slug"]): entry for entry in existing_entries
        })

        if any(str(entry["canonical_slug"]) == slug for entry in existing_entries):
            raise WikiAuthoringError(
                f"An entry with the slug '{slug}' already exists. Edit it instead.",
            )

        rows = await self.wiki_entries.insert_many(
            [
                {
                    "workspace_id": workspace_id,
                    "preferred_label": candidate.label,
                    "canonical_slug": slug,
                    "definition": candidate.definition,
                    "pronunciation": candidate.pronunciation,
                    "aliases": candidate.aliases,
                    "prerequisites": [],
                    "importance": candidate.importance,
                    "entry_kind": candidate.entry_kind,
                    "status": "canonical",
                    "evidence": [],
                    "origin": candidate.origin,
                },
            ],
        )
        await self._embed_entries([str(rows[0]["id"])])
        return rows[0]

    async def update_entry(
        self,
        wiki_entry_id: str,
        workspace_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        row = await self.wiki_entries.get_for_workspace(wiki_entry_id, workspace_id)

        if not row:
            raise WikiIngestNotFoundError("Wiki entry not found.")

        updated = await self.wiki_entries.update(wiki_entry_id, payload)

        if "definition" in payload or "preferred_label" in payload:
            await self._embed_entries([wiki_entry_id])
            updated = await self.wiki_entries.get_for_workspace(wiki_entry_id, workspace_id) or updated

        return updated

    async def deprecate_entry(self, wiki_entry_id: str, workspace_id: str) -> dict[str, Any]:
        row = await self.wiki_entries.get_for_workspace(wiki_entry_id, workspace_id)

        if not row:
            raise WikiIngestNotFoundError("Wiki entry not found.")

        return await self.wiki_entries.update(wiki_entry_id, {"status": "deprecated"})

    # ------------------------------------------------------------------
    # Structuring + enrichment internals
    # ------------------------------------------------------------------

    async def _structure_notes(
        self,
        notes: str,
        *,
        chapter_title: str | None,
    ) -> tuple[dict[str, Any], str, float | None]:
        context = f"These notes are from the chapter: {chapter_title}\n\n" if chapter_title else ""
        user_prompt = f"{context}READER NOTES:\n{notes}"

        result = await asyncio.to_thread(
            self.llm_client.complete_json,
            system_prompt=STRUCTURING_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        raw_entries = result.content.get("entries")
        if not isinstance(raw_entries, list):
            raise WikiAuthoringError("Structuring failed: the model returned no entries.")

        fragments = result.content.get("unparsed_fragments")
        structured = {
            "entries": raw_entries,
            "unparsed_fragments": [
                str(fragment)
                for fragment in (fragments if isinstance(fragments, list) else [])
                if str(fragment).strip()
            ],
        }

        usage = result.token_usage or {}
        cost = cost_llm_usage(
            provider=getattr(result, "provider", "openai") or "openai",
            model=result.model,
            input_tokens=int(usage.get("input_tokens") or 0),
            output_tokens=int(usage.get("output_tokens") or 0),
        )
        return structured, result.model, cost.get("cost_usd")

    async def _enrich_entries(
        self,
        raw_entries: list[Any],
        *,
        workspace_id: str,
        source_id: str | None,
        chapter: dict[str, Any] | None,
    ) -> list[WikiIngestEntry]:
        entries: list[WikiIngestEntry] = []

        for index, raw in enumerate(raw_entries):
            if not isinstance(raw, dict):
                continue

            label = str(raw.get("label") or "").strip()
            definition = str(raw.get("definition") or "").strip()

            if not label or not definition:
                continue

            entries.append(
                WikiIngestEntry(
                    index=index,
                    label=label[:120],
                    entry_kind=self._coerce_choice(
                        raw.get("entry_kind"), {"term", "concept", "insight"}, "concept",
                    ),
                    definition=definition,
                    aliases=[str(alias) for alias in raw.get("aliases") or [] if str(alias).strip()],
                    pronunciation=(str(raw["pronunciation"]) if raw.get("pronunciation") else None),
                    importance=self._coerce_choice(
                        raw.get("importance"),
                        {"essential", "supporting", "contextual"},
                        "supporting",
                    ),
                    prerequisite_labels=[
                        str(item) for item in raw.get("prerequisite_labels") or [] if str(item).strip()
                    ],
                    note_excerpt=str(raw.get("note_excerpt") or "")[:240],
                ),
            )

        # Re-index after dropping malformed items so indexes stay contiguous.
        for index, entry in enumerate(entries):
            entry.index = index

        existing_entries = await self._list_all_entries(workspace_id)
        entries = self._refresh_resolutions(entries, existing_entries)

        if entries:
            await self._attach_evidence_and_similars(
                entries,
                workspace_id=workspace_id,
                source_id=source_id,
                chapter=chapter,
            )

        return entries

    @staticmethod
    def _coerce_choice(value: Any, allowed: set[str], default: str) -> str:
        candidate = str(value or "").strip().lower()
        return candidate if candidate in allowed else default

    def _refresh_resolutions(
        self,
        entries: list[WikiIngestEntry],
        existing_entries: list[dict[str, Any]],
    ) -> list[WikiIngestEntry]:
        entries_by_slug = {
            str(entry["canonical_slug"]): entry for entry in existing_entries
        }
        refreshed: list[WikiIngestEntry] = []

        for entry in entries:
            candidate = WikiCandidate(
                label=entry.label,
                definition=entry.definition,
                entry_kind=entry.entry_kind,
            )
            slug = candidate_slug(candidate, entries_by_slug)
            existing = entries_by_slug.get(slug)

            updated = entry.model_copy(deep=True)
            updated.canonical_slug = slug

            if not existing:
                updated.resolution = "new"
                updated.existing_entry_id = None
                updated.existing_definition = None
            else:
                updated.existing_entry_id = str(existing.get("id") or "") or None
                updated.existing_definition = str(existing.get("definition") or "")
                updated.resolution = (
                    "conflict"
                    if definitions_conflict(updated.existing_definition, entry.definition)
                    else "merge"
                )

            refreshed.append(updated)

        return refreshed

    async def _attach_evidence_and_similars(
        self,
        entries: list[WikiIngestEntry],
        *,
        workspace_id: str,
        source_id: str | None,
        chapter: dict[str, Any] | None,
    ) -> None:
        texts = [_embedding_text(entry.label, entry.definition) for entry in entries]
        vectors = await asyncio.to_thread(self.embedding_client.embed, texts)

        wiki_settings = self.settings.wiki_authoring
        chapter_segment_ids = set(
            str(segment_id) for segment_id in (chapter or {}).get("segment_ids") or []
        )
        fetch_count = (
            wiki_settings.evidence_top_k * _CHAPTER_OVERFETCH
            if chapter_segment_ids
            else wiki_settings.evidence_top_k
        )

        for entry, vector in zip(entries, vectors):
            if source_id:
                rows = await self.retrieval.match_segments(
                    embedding=vector,
                    workspace_id=workspace_id,
                    threshold=wiki_settings.evidence_weak_floor,
                    count=fetch_count,
                    source_ids=[source_id],
                )

                if chapter_segment_ids:
                    scoped = [row for row in rows if str(row["id"]) in chapter_segment_ids]
                    rows = scoped or rows

                rows = rows[: wiki_settings.evidence_top_k]
                entry.evidence = [
                    WikiIngestEvidence(
                        segment_id=str(row["id"]),
                        sequence_index=row.get("sequence_index"),
                        page=(row.get("locator") or {}).get("page"),
                        similarity=round(float(row.get("similarity") or 0.0), 4),
                        preview=str(row.get("text") or "")[:280],
                        reader_link=build_reader_link(
                            str(row["source_id"]),
                            int(row.get("sequence_index") or 0),
                        ),
                    )
                    for row in rows
                ]
                best = max((float(row.get("similarity") or 0.0) for row in rows), default=0.0)

                if best >= wiki_settings.evidence_threshold:
                    entry.evidence_status = "linked"
                elif entry.evidence:
                    entry.evidence_status = "weak"
                else:
                    entry.evidence_status = "unlinked"
            else:
                entry.evidence = []
                entry.evidence_status = "unlinked"

            similar_rows = await self.retrieval.match_wiki_entries(
                embedding=vector,
                workspace_id=workspace_id,
                threshold=wiki_settings.dedup_similarity_threshold,
                count=3,
            )
            entry.similar_entries = [
                WikiIngestSimilarEntry(
                    id=str(row["id"]),
                    label=str(row.get("preferred_label") or ""),
                    similarity=round(float(row.get("similarity") or 0.0), 4),
                )
                for row in similar_rows
                if str(row.get("canonical_slug") or "") != entry.canonical_slug
            ]

    def _entry_to_candidate(
        self,
        entry: WikiIngestEntry,
        *,
        batch_id: str,
        source_id: str | None,
        chapter: dict[str, Any],
    ) -> WikiCandidate:
        evidence: list[dict[str, Any]] = []

        if source_id:
            for record in entry.evidence:
                evidence.append(
                    {
                        "source_id": source_id,
                        "segment_id": record.segment_id,
                        "sequence_index": record.sequence_index,
                        "page": record.page,
                        "reader_link": record.reader_link,
                    },
                )

        origin: dict[str, Any] = {
            "kind": "manual",
            "batch_id": batch_id,
            "note_excerpt": entry.note_excerpt,
        }
        if source_id:
            origin["source_id"] = source_id
        if chapter.get("chapter_id"):
            origin["chapter_id"] = chapter["chapter_id"]
        if chapter.get("sequence_index") is not None:
            origin["chapter_sequence_index"] = chapter["sequence_index"]

        return WikiCandidate(
            label=entry.label,
            definition=entry.definition,
            entry_kind=entry.entry_kind,
            aliases=entry.aliases,
            prerequisite_labels=entry.prerequisite_labels,
            pronunciation=entry.pronunciation,
            importance=entry.importance,
            evidence=evidence,
            origin=origin,
        )

    async def _resolve_chapter(
        self,
        chapter_hint: str | None,
        source_id: str | None,
    ) -> dict[str, Any] | None:
        """Resolve a chapter number or title fragment against document_chapters.

        The stored block keeps ``segment_ids`` (for evidence scoping) alongside
        the contract's display fields; responses expose only the display fields.
        """
        if not chapter_hint or not source_id:
            return None

        hint = chapter_hint.strip()
        if not hint:
            return None

        rows = await self.batches.list_chapters_for_source(source_id)

        matched: dict[str, Any] | None = None
        if hint.isdigit():
            wanted = int(hint)
            matched = next(
                (row for row in rows if int(row.get("sequence_index") or -1) == wanted),
                None,
            )

        if matched is None:
            lowered = hint.lower()
            matched = next(
                (row for row in rows if lowered in str(row.get("title") or "").lower()),
                None,
            )

        if matched is None:
            return None

        section_segment_ids = [
            str(segment_id)
            for section in matched.get("sections") or []
            for segment_id in section.get("segment_ids") or []
        ]
        return {
            "chapter_id": str(matched["id"]),
            "title": str(matched.get("title") or "Untitled"),
            "sequence_index": int(matched.get("sequence_index") or 0),
            "segment_ids": [
                *(str(segment_id) for segment_id in matched.get("segment_ids") or []),
                *section_segment_ids,
            ],
        }

    async def _require_batch(
        self,
        batch_id: str,
        workspace_id: str,
        *,
        allowed: set[str],
    ) -> dict[str, Any]:
        batch = await self.batches.get_for_workspace(batch_id, workspace_id)

        if not batch:
            raise WikiIngestNotFoundError("Ingest batch not found.")

        status = batch.get("status")
        if status not in allowed:
            allowed_list = ", ".join(sorted(allowed))
            raise WikiAuthoringError(
                f"Batch is {status}; expected one of: {allowed_list}.",
            )

        return batch

    async def _list_all_entries(self, workspace_id: str) -> list[dict[str, Any]]:
        # All statuses: the slug-uniqueness constraint spans deprecated and
        # disputed rows too, so resolution must see them.
        return await self.wiki_entries.list_for_workspace(workspace_id, limit=1000)

    async def _embed_entries(self, wiki_entry_ids: list[str]) -> None:
        if not wiki_entry_ids:
            return

        rows = await self.wiki_entries.get_many(wiki_entry_ids)

        if not rows:
            return

        texts = [
            _embedding_text(
                str(row.get("preferred_label") or ""),
                str(row.get("definition") or ""),
            )
            for row in rows
        ]
        vectors = await asyncio.to_thread(self.embedding_client.embed, texts)
        now = _utc_now_iso()

        for row, vector in zip(rows, vectors):
            await self.wiki_entries.update(
                str(row["id"]),
                {"embedding": to_pgvector_literal(vector), "embedded_at": now},
            )
