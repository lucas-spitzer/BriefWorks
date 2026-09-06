from __future__ import annotations

import asyncio
from typing import Any

import pytest

from app.models.wiki_ingest import WikiIngestCreate, WikiIngestEntry
from app.services.wiki_authoring import (
    WikiAuthoringError,
    WikiAuthoringService,
    WikiIngestDriftError,
)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeWikiEntryRepository:
    def __init__(self, rows: list[dict[str, Any]] | None = None) -> None:
        self.rows: dict[str, dict[str, Any]] = {
            str(row["id"]): row for row in (rows or [])
        }
        self._next_id = 1

    async def list_for_workspace(self, workspace_id: str, **_kwargs) -> list[dict[str, Any]]:
        return [row for row in self.rows.values() if row["workspace_id"] == workspace_id]

    async def get_for_workspace(self, wiki_entry_id: str, workspace_id: str):
        row = self.rows.get(wiki_entry_id)
        return row if row and row["workspace_id"] == workspace_id else None

    async def get_many(self, wiki_entry_ids: list[str]) -> list[dict[str, Any]]:
        return [self.rows[entry_id] for entry_id in wiki_entry_ids if entry_id in self.rows]

    async def insert_many(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        created = []
        for row in rows:
            row = {**row, "id": f"wiki-{self._next_id}"}
            self._next_id += 1
            self.rows[row["id"]] = row
            created.append(row)
        return created

    async def update(self, wiki_entry_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.rows[wiki_entry_id] = {**self.rows[wiki_entry_id], **payload}
        return self.rows[wiki_entry_id]


class _FakeBatchDb:
    async def select_one(self, table: str, *, filters: dict[str, str], columns: str = "*"):
        del table, filters, columns
        return {"id": "ws-1", "slug": "ocs-prep"}


class FakeBatchRepository:
    def __init__(
        self,
        chapters: list[dict[str, Any]] | None = None,
        *,
        has_segments: bool = True,
    ) -> None:
        self.rows: dict[str, dict[str, Any]] = {}
        self.chapters = chapters or []
        self.has_segments = has_segments
        self._next_id = 1
        self.db = _FakeBatchDb()

    async def list_for_workspace(self, workspace_id: str, **_kwargs) -> list[dict[str, Any]]:
        return [row for row in self.rows.values() if row["workspace_id"] == workspace_id]

    async def get_for_workspace(self, batch_id: str, workspace_id: str):
        row = self.rows.get(batch_id)
        return row if row and row["workspace_id"] == workspace_id else None

    async def insert(self, payload: dict[str, Any]) -> dict[str, Any]:
        row_id = str(payload.get("id") or f"batch-{self._next_id}")
        if "id" not in payload:
            self._next_id += 1
        row = {**payload, "id": row_id}
        self.rows[row["id"]] = row
        return row

    async def update(self, batch_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.rows[batch_id] = {**self.rows[batch_id], **payload}
        return self.rows[batch_id]

    async def list_chapters_for_source(self, source_id: str) -> list[dict[str, Any]]:
        return self.chapters

    async def source_has_segments(self, source_id: str) -> bool:
        return self.has_segments


class FakeRetrievalRepository:
    """Segment matches keyed by entry label prefix via the embedding vector.

    The fake embedding client encodes each text's position, and this repo maps
    positions to canned matches, so tests control per-entry evidence.
    """

    def __init__(
        self,
        segment_matches: dict[int, list[dict[str, Any]]] | None = None,
        wiki_matches: list[dict[str, Any]] | None = None,
    ) -> None:
        self.segment_matches = segment_matches or {}
        self.wiki_matches = wiki_matches or []

    async def match_segments(self, *, embedding, threshold, **_kwargs):
        position = int(embedding[0])
        rows = self.segment_matches.get(position, [])
        return [row for row in rows if row["similarity"] >= threshold]

    async def match_wiki_entries(self, *, embedding, threshold, **_kwargs):
        return [row for row in self.wiki_matches if row["similarity"] >= threshold]


class FakeEmbeddingClient:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(texts)
        # Position-coded vectors so the retrieval fake can key off them.
        return [[float(index)] * 3 for index in range(len(texts))]


class FakeLLMClient:
    provider = "openai"
    model = "fake-model"

    def __init__(self, content: dict[str, Any]) -> None:
        self.content = content
        self.calls: list[dict[str, str]] = []

    def complete_json(self, *, system_prompt: str, user_prompt: str, model=None):
        self.calls.append({"system": system_prompt, "user": user_prompt})

        class _Result:
            content = self.content
            model = "fake-model"
            provider = "openai"
            token_usage = {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150}

        return _Result()


def _service(
    *,
    llm_content: dict[str, Any] | None = None,
    wiki_rows: list[dict[str, Any]] | None = None,
    segment_matches: dict[int, list[dict[str, Any]]] | None = None,
    wiki_matches: list[dict[str, Any]] | None = None,
    chapters: list[dict[str, Any]] | None = None,
    has_segments: bool = True,
    storage: Any | None = None,
) -> WikiAuthoringService:
    return WikiAuthoringService(
        wiki_entries=FakeWikiEntryRepository(wiki_rows),  # type: ignore[arg-type]
        batches=FakeBatchRepository(chapters, has_segments=has_segments),  # type: ignore[arg-type]
        retrieval=FakeRetrievalRepository(segment_matches, wiki_matches),  # type: ignore[arg-type]
        embedding_client=FakeEmbeddingClient(),
        llm_client=FakeLLMClient(llm_content or {"entries": [], "unparsed_fragments": []}),
        storage=storage,
    )


def _segment_row(segment_id: str, similarity: float) -> dict[str, Any]:
    return {
        "id": segment_id,
        "source_id": "src-1",
        "sequence_index": 42,
        "kind": "paragraph",
        "text": "The enemy is a system composed of numerous subsystems.",
        "locator": {"page": 87},
        "similarity": similarity,
    }


def _existing_wiki_row(
    slug: str,
    label: str,
    definition: str,
    *,
    workspace_id: str = "ws-1",
) -> dict[str, Any]:
    return {
        "id": f"wiki-existing-{slug}",
        "workspace_id": workspace_id,
        "canonical_slug": slug,
        "preferred_label": label,
        "definition": definition,
        "entry_kind": "concept",
        "importance": "supporting",
        "aliases": [],
        "prerequisites": [],
        "status": "canonical",
        "evidence": [],
        "origin": {},
    }


_STRUCTURED = {
    "entries": [
        {
            "label": "Enemy System",
            "entry_kind": "concept",
            "definition": "The enemy as a system of interdependent parts.",
            "aliases": ["five-ring model"],
            "pronunciation": None,
            "importance": "essential",
            "prerequisite_labels": [],
            "note_excerpt": "Enemy system — Warden's idea…",
        },
        {
            "label": "Tempo",
            "entry_kind": "term",
            "definition": "The rate of operations relative to the enemy.",
            "aliases": [],
            "pronunciation": None,
            "importance": "supporting",
            "prerequisite_labels": ["Enemy System"],
            "note_excerpt": "tempo: rate of ops…",
        },
    ],
    "unparsed_fragments": ["something about page 12?"],
}


# ---------------------------------------------------------------------------
# create_batch
# ---------------------------------------------------------------------------


def test_create_batch_structures_and_enriches() -> None:
    service = _service(
        llm_content=_STRUCTURED,
        segment_matches={
            0: [_segment_row("seg-1", 0.63)],  # Enemy System: linked
            1: [_segment_row("seg-2", 0.35)],  # Tempo: weak (below 0.45 threshold)
        },
    )

    batch = asyncio.run(
        service.create_batch(
            WikiIngestCreate(notes="Enemy system…\ntempo: rate of ops", source_id="src-1"),
            "ws-1",
        ),
    )

    assert batch["status"] == "draft"
    assert batch["unparsed_fragments"] == ["something about page 12?"]
    assert batch["model"] == "fake-model"
    assert batch["cost_usd"] is not None

    entries = batch["entries"]
    assert [entry["canonical_slug"] for entry in entries] == ["enemy-system", "tempo"]
    assert all(entry["resolution"] == "new" for entry in entries)

    enemy, tempo = entries
    assert enemy["evidence_status"] == "linked"
    assert enemy["evidence"][0]["segment_id"] == "seg-1"
    assert enemy["evidence"][0]["reader_link"] == "/app/reader/src-1?seg=42"
    assert tempo["evidence_status"] == "weak"


def test_create_batch_flags_merge_and_conflict_against_existing_wiki() -> None:
    existing = [
        _existing_wiki_row(
            "enemy-system",
            "Enemy System",
            # Prefix of the proposed definition → compatible merge.
            "The enemy as a system",
        ),
        _existing_wiki_row(
            "tempo",
            "Tempo",
            "Tempo is a musical term.",
        ),
    ]
    service = _service(llm_content=_STRUCTURED, wiki_rows=existing)

    batch = asyncio.run(
        service.create_batch(WikiIngestCreate(notes="notes"), "ws-1"),
    )

    enemy, tempo = batch["entries"]
    assert enemy["resolution"] == "merge"
    assert enemy["existing_entry_id"] == "wiki-existing-enemy-system"
    assert tempo["resolution"] == "conflict"
    assert tempo["existing_definition"] == "Tempo is a musical term."


def test_create_batch_without_source_leaves_entries_unlinked() -> None:
    service = _service(llm_content=_STRUCTURED)

    batch = asyncio.run(service.create_batch(WikiIngestCreate(notes="notes"), "ws-1"))

    assert all(entry["evidence_status"] == "unlinked" for entry in batch["entries"])
    assert all(entry["evidence"] == [] for entry in batch["entries"])


def test_create_batch_resolves_chapter_hint_and_scopes_evidence() -> None:
    chapters = [
        {
            "id": "ch-3",
            "title": "The Enemy as a System",
            "sequence_index": 3,
            "segment_ids": ["seg-1"],
            "sections": [],
        },
    ]
    service = _service(
        llm_content=_STRUCTURED,
        chapters=chapters,
        segment_matches={
            # seg-9 is outside the chapter: it must be filtered out in favor of seg-1.
            0: [_segment_row("seg-9", 0.7), _segment_row("seg-1", 0.6)],
            1: [],
        },
    )

    batch = asyncio.run(
        service.create_batch(
            WikiIngestCreate(notes="notes", source_id="src-1", chapter_hint="3"),
            "ws-1",
        ),
    )

    assert batch["chapter"]["chapter_id"] == "ch-3"
    assert batch["chapter"]["title"] == "The Enemy as a System"
    enemy = batch["entries"][0]
    assert [record["segment_id"] for record in enemy["evidence"]] == ["seg-1"]


def test_create_batch_rejects_oversized_notes() -> None:
    service = _service()
    huge_notes = "x" * (service.settings.wiki_authoring.max_notes_chars + 1)

    with pytest.raises(WikiAuthoringError, match="exceed"):
        asyncio.run(service.create_batch(WikiIngestCreate(notes=huge_notes), "ws-1"))


# ---------------------------------------------------------------------------
# commit_batch
# ---------------------------------------------------------------------------


def _run_create(service: WikiAuthoringService, **kwargs) -> dict[str, Any]:
    return asyncio.run(
        service.create_batch(
            WikiIngestCreate(notes="notes", **kwargs),
            "ws-1",
        ),
    )


def test_commit_inserts_entries_embeds_and_marks_committed() -> None:
    service = _service(
        llm_content=_STRUCTURED,
        segment_matches={0: [_segment_row("seg-1", 0.63)], 1: []},
    )
    batch = _run_create(service, source_id="src-1")

    committed, inserted_ids, updated_ids = asyncio.run(
        service.commit_batch(batch["id"], "ws-1"),
    )

    assert committed["status"] == "committed"
    assert committed["committed_at"]
    assert len(inserted_ids) == 2
    assert updated_ids == []

    rows = asyncio.run(service.wiki_entries.list_for_workspace("ws-1"))
    by_slug = {row["canonical_slug"]: row for row in rows}
    enemy = by_slug["enemy-system"]
    assert enemy["status"] == "canonical"
    # Committed evidence keeps the reader deep-link fields so wiki entries can
    # jump straight to the cited passage.
    assert enemy["evidence"] == [
        {
            "source_id": "src-1",
            "segment_id": "seg-1",
            "sequence_index": 42,
            "page": 87,
            "reader_link": "/app/reader/src-1?seg=42",
        }
    ]
    assert enemy["origin"]["kind"] == "manual"
    assert enemy["origin"]["batch_id"] == batch["id"]
    assert enemy["origin"]["source_id"] == "src-1"
    # Every committed entry is embedded for the assistant's precision channel.
    assert enemy["embedding"]
    assert enemy["embedded_at"]

    # Tempo's prerequisite label resolved to the Enemy System entry id.
    tempo = by_slug["tempo"]
    assert tempo["prerequisites"] == [enemy["id"]]


def test_commit_conflict_overrides_with_reviewed_definition() -> None:
    existing = [_existing_wiki_row("tempo", "Tempo", "Tempo is a musical term.")]
    service = _service(llm_content=_STRUCTURED, wiki_rows=existing)
    batch = _run_create(service)
    assert batch["entries"][1]["resolution"] == "conflict"

    _, inserted_ids, updated_ids = asyncio.run(service.commit_batch(batch["id"], "ws-1"))

    assert len(inserted_ids) == 1  # Enemy System
    assert updated_ids == ["wiki-existing-tempo"]
    tempo = asyncio.run(
        service.wiki_entries.get_for_workspace("wiki-existing-tempo", "ws-1"),
    )
    assert tempo["definition"] == "The rate of operations relative to the enemy."


def test_commit_detects_drift_and_refreshes_batch() -> None:
    service = _service(llm_content=_STRUCTURED)
    batch = _run_create(service)
    assert all(entry["resolution"] == "new" for entry in batch["entries"])

    # Another batch lands the same slug with a conflicting definition after review.
    asyncio.run(
        service.wiki_entries.insert_many(
            [
                {
                    **_existing_wiki_row("tempo", "Tempo", "Tempo is a musical term."),
                    "id": None,
                },
            ],
        ),
    )

    with pytest.raises(WikiIngestDriftError) as exc:
        asyncio.run(service.commit_batch(batch["id"], "ws-1"))

    assert exc.value.drifted_indexes == [1]
    refreshed = exc.value.batch["entries"][1]
    assert refreshed["resolution"] == "conflict"

    # The batch is still a draft: re-confirming (committing again) now succeeds.
    _, inserted_ids, updated_ids = asyncio.run(service.commit_batch(batch["id"], "ws-1"))
    assert len(inserted_ids) == 1
    assert len(updated_ids) == 1


def test_commit_requires_included_entries() -> None:
    service = _service(llm_content=_STRUCTURED)
    batch = _run_create(service)

    entries = [WikiIngestEntry.model_validate(entry) for entry in batch["entries"]]
    for entry in entries:
        entry.include = False
    asyncio.run(service.update_batch(batch["id"], "ws-1", entries=entries))

    with pytest.raises(WikiAuthoringError, match="inclusion"):
        asyncio.run(service.commit_batch(batch["id"], "ws-1"))


def test_commit_rejects_non_draft_batches() -> None:
    service = _service(llm_content=_STRUCTURED)
    batch = _run_create(service)
    asyncio.run(service.discard_batch(batch["id"], "ws-1"))

    with pytest.raises(WikiAuthoringError, match="discarded"):
        asyncio.run(service.commit_batch(batch["id"], "ws-1"))


# ---------------------------------------------------------------------------
# Entry CRUD
# ---------------------------------------------------------------------------


def test_create_entry_quick_add_inserts_and_embeds() -> None:
    service = _service()

    row = asyncio.run(
        service.create_entry(
            "ws-1",
            preferred_label="OODA Loop",
            definition="Observe, orient, decide, act.",
            entry_kind="concept",
            importance="essential",
            aliases=["Boyd cycle"],
            pronunciation=None,
        ),
    )

    assert row["canonical_slug"] == "ooda-loop"
    assert row["origin"] == {"kind": "manual"}
    stored = asyncio.run(service.wiki_entries.get_for_workspace(row["id"], "ws-1"))
    assert stored["embedding"]


def test_create_entry_accepts_reader_define_origin() -> None:
    service = _service()

    row = asyncio.run(
        service.create_entry(
            "ws-1",
            preferred_label="Tempo",
            definition="The pace of decisions in a fight.",
            entry_kind="term",
            importance="supporting",
            aliases=[],
            pronunciation=None,
            origin={
                "kind": "reader_define",
                "mode": "contextual",
                "source_id": "src-1",
                "term": "Tempo",
            },
        ),
    )

    assert row["origin"]["kind"] == "reader_define"
    assert row["origin"]["mode"] == "contextual"
    assert row["status"] == "canonical"


def test_create_entry_rejects_duplicate_slug() -> None:
    service = _service(
        wiki_rows=[_existing_wiki_row("ooda-loop", "OODA Loop", "def")],
    )

    with pytest.raises(WikiAuthoringError, match="already exists"):
        asyncio.run(
            service.create_entry(
                "ws-1",
                preferred_label="OODA Loop",
                definition="def",
                entry_kind="concept",
                importance="supporting",
                aliases=[],
                pronunciation=None,
            ),
        )


def test_deprecate_entry_sets_status() -> None:
    service = _service(
        wiki_rows=[_existing_wiki_row("tempo", "Tempo", "def")],
    )

    row = asyncio.run(service.deprecate_entry("wiki-existing-tempo", "ws-1"))

    assert row["status"] == "deprecated"


# ---------------------------------------------------------------------------
# File ingest + structure_batch
# ---------------------------------------------------------------------------


class FakeStorage:
    def __init__(self) -> None:
        self.uploads: list[dict[str, Any]] = []

    async def upload(
        self,
        *,
        bucket: str,
        path: str,
        content: bytes,
        content_type: str,
        upsert: bool = False,
    ):
        self.uploads.append(
            {
                "bucket": bucket,
                "path": path,
                "content": content,
                "content_type": content_type,
            },
        )
        return {}


def test_create_file_batch_requires_source_id(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _service(storage=FakeStorage())
    monkeypatch.setattr(
        "app.services.wiki_authoring.enqueue_wiki_ingest_transcription",
        lambda *_args, **_kwargs: "job-1",
    )

    with pytest.raises(WikiAuthoringError, match="source_id is required"):
        asyncio.run(
            service.create_file_batch(
                workspace_id="ws-1",
                source_id="",
                chapter_hint=None,
                title=None,
                files=[("notes.md", "text/markdown", b"term: def")],
            ),
        )


def test_create_file_batch_requires_segments(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _service(storage=FakeStorage(), has_segments=False)
    monkeypatch.setattr(
        "app.services.wiki_authoring.enqueue_wiki_ingest_transcription",
        lambda *_args, **_kwargs: "job-1",
    )

    with pytest.raises(WikiAuthoringError, match="no parsed segments"):
        asyncio.run(
            service.create_file_batch(
                workspace_id="ws-1",
                source_id="src-1",
                chapter_hint=None,
                title=None,
                files=[("notes.md", "text/markdown", b"term: def")],
            ),
        )


def test_create_file_batch_stores_attachments_and_enqueues(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage = FakeStorage()
    service = _service(storage=storage)
    enqueued: list[str] = []
    monkeypatch.setattr(
        "app.services.wiki_authoring.enqueue_wiki_ingest_transcription",
        lambda _settings, batch_id: enqueued.append(batch_id) or "job-1",
    )

    batch = asyncio.run(
        service.create_file_batch(
            workspace_id="ws-1",
            source_id="src-1",
            chapter_hint="3",
            title="Ch. 3 photos",
            files=[
                ("page1.md", "text/markdown", "Enemy system - interdependent parts".encode()),
                ("page2.txt", "text/plain", b"insight: tempo wins"),
            ],
        ),
    )

    assert batch["status"] == "transcribing"
    assert batch["raw_notes"] == ""
    assert batch["source_id"] == "src-1"
    assert len(batch["attachments"]) == 2
    assert batch["attachments"][0]["filename"] == "page1.md"
    assert len(storage.uploads) == 2
    assert enqueued == [batch["id"]]


def test_structure_batch_from_transcribed_notes() -> None:
    service = _service(llm_content=_STRUCTURED)
    batch_id = "batch-tx"
    service.batches.rows[batch_id] = {
        "id": batch_id,
        "workspace_id": "ws-1",
        "source_id": "src-1",
        "title": "Notes",
        "raw_notes": "Enemy system…\ntempo: rate of ops",
        "chapter_hint": None,
        "chapter": None,
        "status": "transcribed",
        "entries": [],
        "unparsed_fragments": [],
        "attachments": [],
    }

    updated = asyncio.run(service.structure_batch(batch_id, "ws-1"))

    assert updated["status"] == "draft"
    assert len(updated["entries"]) == 2
    assert updated["unparsed_fragments"] == ["something about page 12?"]


def test_update_batch_allows_raw_notes_while_transcribed() -> None:
    service = _service()
    batch_id = "batch-tx"
    service.batches.rows[batch_id] = {
        "id": batch_id,
        "workspace_id": "ws-1",
        "source_id": "src-1",
        "title": "Notes",
        "raw_notes": "old",
        "chapter_hint": None,
        "chapter": None,
        "status": "transcribed",
        "entries": [],
        "unparsed_fragments": [],
        "attachments": [],
    }

    updated = asyncio.run(
        service.update_batch(batch_id, "ws-1", raw_notes="corrected OCR notes"),
    )

    assert updated["raw_notes"] == "corrected OCR notes"
    assert updated["status"] == "transcribed"
