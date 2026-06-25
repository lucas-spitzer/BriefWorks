from __future__ import annotations

import json
from typing import Any

from app.config import get_settings
from app.intellex.chapter_formatting import batch_chapter_segments_for_llm
from app.intellex.selection import (
    calibrate_importance,
    ensure_objective_coverage,
    objective_concept_slugs,
    resolve_canonical_selection,
    selection_score,
)
from app.intellex.stages.concept_models import (
    ChapterKnowledgeOutput,
    DeconstructedConcept,
    ExtractChapterKnowledgeOutput,
    LearningObjective,
    merge_group,
    pick_entry_kind,
)
from app.intellex.wiki_slug import normalize_slug
from app.mathesys.chapter_grouping import hydrate_chapters_from_rows
from app.services.embeddings import EmbeddingClient, get_embedding_client
from app.services.llm import LLMClient, get_llm_client

_IMPORTANCE_ORDER = {"essential": 3, "supporting": 2, "contextual": 1}

_TYPOGRAPHIC_MAP = str.maketrans(
    {
        "‘": "'",
        "’": "'",
        "“": '"',
        "”": '"',
        "–": "-",
        "—": "-",
        "…": "...",
    },
)


def _normalize_for_match(text: str) -> str:
    return " ".join(text.translate(_TYPOGRAPHIC_MAP).lower().split())


def quote_supported_by_segment(quote: str, segment_text: str) -> bool:
    """True when an evidence quote actually appears in its cited segment.

    Normalizes typographic punctuation, case, and whitespace so minor formatting
    differences don't reject a genuine quote; an empty quote is never support.
    """
    normalized_quote = _normalize_for_match(quote)
    if not normalized_quote:
        return False
    return normalized_quote in _normalize_for_match(segment_text)



OBJECTIVES_SYSTEM_PROMPT = """You derive learning objectives for a single document chapter.

Objectives describe what a reader should be able to do after studying this chapter.
Use Bloom's taxonomy levels: remember, understand, apply, analyze.

Return valid JSON with a top-level "objectives" array only. Each objective has:
- "objective_id": short stable id (e.g. "ch1-obj-1")
- "statement": "After this chapter, the reader should be able to…"
- "bloom_level": one of remember, understand, apply, analyze
- "concept_labels": array of term/concept labels this objective covers (may be empty initially)"""

OBJECTIVES_USER_TEMPLATE = """Source metadata:
{source_metadata}

Chapter:
- chapter_id: {chapter_id}
- title: {chapter_title}
- sequence_index: {sequence_index}

Chapter segments:
{segments_json}

Return JSON:
{{ "objectives": [ {{ "objective_id": "ch1-obj-1", "statement": "...", "bloom_level": "understand", "concept_labels": [] }} ] }}"""

CONCEPTS_SYSTEM_PROMPT = """You extract learning knowledge from a single document chapter.

Your job is EXTRACTION, not summarization. Identify what a reader must understand from this chapter only.
Map each item to the provided learning objectives via objective_labels when applicable.

Each item is a JSON object with EXACTLY these keys:
- "entry_kind": one of "term", "concept", or "insight"
- "term_label": string — canonical name or insight headline
- "definition": string — definition (term/concept) or explanatory insight text grounded in the chapter
- "aliases": array of strings (use [] if none)
- "prerequisite_labels": array of strings (use [] if none)
- "pronunciation": string or null — phonetic hint for acronyms/uncommon terms
- "importance": one of "essential", "supporting", or "contextual"
- "evidence_segment_ids": array of segment_id strings from the provided chapter segments
- "evidence_quotes": array of {{"segment_id": "...", "quote": "exact supporting text from segment"}}
- "objective_labels": array of objective_id strings from the provided objectives
- "confidence": number from 0.0 to 1.0

entry_kind rules:
- "term": vocabulary, acronyms, named entities the reader must know
- "concept": ideas, principles, frameworks defined or central to the chapter
- "insight": non-vocabulary takeaways — causal relationships, doctrinal implications, lessons grounded in chapter text

Rules:
- Ground every item in the provided chapter segments only.
- Cite evidence_segment_ids and include exact evidence_quotes from segment text.
- Do not duplicate the same item under different labels; use aliases instead.
- Do not summarize the whole chapter.
- Return valid JSON with a top-level "items" array only."""

CONCEPTS_USER_TEMPLATE = """Source metadata:
{source_metadata}

Chapter:
- chapter_id: {chapter_id}
- title: {chapter_title}
- sequence_index: {sequence_index}
- level: {chapter_level}

Learning objectives for this chapter:
{objectives_json}

Chapter segments:
{segments_json}

Existing workspace labels (deduplicate using aliases when these match):
{existing_labels}

Return JSON in exactly this shape:
{{ "items": [ {{ "entry_kind": "concept", "term_label": "string", "definition": "string", "aliases": [], "prerequisite_labels": [], "pronunciation": null, "importance": "essential", "evidence_segment_ids": ["string"], "evidence_quotes": [{{"segment_id": "string", "quote": "string"}}], "objective_labels": [], "confidence": 0.0 }} ] }}"""

CONSOLIDATION_SYSTEM_PROMPT = """You consolidate extracted knowledge across an entire document.

Semantically merge near-duplicate concepts (same idea, different labels) into one entry.
Re-assign global importance: a concept supporting in one chapter may be essential document-wide.
Preserve evidence_segment_ids from merged items. Omit evidence_quotes unless essential.

Return valid JSON with a top-level "items" array using the same schema as the input items.
Keep the response compact — do not repeat long definitions verbatim if labels match."""

CURATION_SYSTEM_PROMPT = """You are the wiki editor for a learning knowledge base.

From the candidate entries extracted from one document, select the ones that
deserve a durable, canonical wiki entry. Favor entries that are well grounded in
evidence, central to the document's learning objectives, and genuinely worth
remembering. Reject redundant, trivial, or thinly supported candidates.

Select no more than the requested budget. Returning fewer is fine when fewer are
worthy. Return valid JSON only:
{ "canonical_labels": ["exact term_label", ...] }
Use term_label values exactly as provided; do not invent new ones."""

CURATION_USER_TEMPLATE = """Source metadata:
{source_metadata}

Budget: select at most {budget} entries as canonical.

Candidate entries (each with its selection signals):
{candidates_json}

Return JSON: {{ "canonical_labels": ["exact term_label", ...] }}"""

_CONSOLIDATION_BATCH_SIZE = 40


def _slim_concept_for_consolidation(item: DeconstructedConcept) -> dict[str, Any]:
    return {
        "term_label": item.term_label,
        "definition": item.definition[:500],
        "entry_kind": item.entry_kind,
        "aliases": item.aliases,
        "importance": item.importance,
        "evidence_segment_ids": item.evidence_segment_ids,
        "chapter_id": item.chapter_id,
        "confidence": item.confidence,
    }

CONSOLIDATION_USER_TEMPLATE = """Source metadata:
{source_metadata}

Extracted concepts (may contain cross-chapter duplicates):
{items_json}

Return consolidated JSON:
{{ "items": [ ... ] }}"""


def _deep_importance_levels() -> set[str]:
    return set(get_settings().intellex.extract_knowledge_deep_importance)


def _chapter_salience(sequence_index: int, chapter_count: int, segment_count: int) -> float:
    if chapter_count <= 1:
        return 1.0
    position_score = 1.0 - (sequence_index / max(chapter_count - 1, 1))
    size_score = min(segment_count / 20.0, 1.0)
    return (position_score * 0.6) + (size_score * 0.4)


class ExtractChapterKnowledgeStage:
    def __init__(
        self,
        *,
        llm_client: LLMClient | None = None,
        embedding_client: EmbeddingClient | None = None,
    ) -> None:
        self._llm_client = llm_client
        self._embedding_client = embedding_client

    @property
    def llm_client(self) -> LLMClient:
        # Resolved lazily so workspace overrides set at run time are honored.
        if self._llm_client is None:
            self._llm_client = get_llm_client("extract_knowledge")
        return self._llm_client

    @property
    def embedding_client(self) -> EmbeddingClient:
        if self._embedding_client is None:
            self._embedding_client = get_embedding_client()
        return self._embedding_client

    def run(
        self,
        *,
        source_metadata: dict[str, Any],
        chapter_rows: list[dict[str, Any]],
        segments: list[dict[str, Any]],
        existing_labels: list[str] | None = None,
    ) -> tuple[ExtractChapterKnowledgeOutput, dict[str, Any]]:
        if not chapter_rows:
            raise RuntimeError("Document chapters are required for knowledge extraction.")

        segment_index = {str(segment["id"]): segment for segment in segments}
        sorted_chapters = sorted(chapter_rows, key=lambda row: row.get("sequence_index", 0))
        chapter_outputs: list[ChapterKnowledgeOutput] = []
        all_objectives: list[LearningObjective] = []
        token_usage: dict[str, int] = {}
        provider = self.llm_client.provider
        model = self.llm_client.model

        for chapter_row in sorted_chapters:
            chapter_id = str(chapter_row["id"])
            hydrated = hydrate_chapters_from_rows([chapter_row], segment_index)

            if not hydrated:
                raise RuntimeError(f"Chapter {chapter_id} has no resolvable segments.")

            chapter_segments = hydrated[0]["segments"]
            chapter_title = str(chapter_row.get("title") or hydrated[0].get("title") or "Untitled")
            sequence_index = int(chapter_row.get("sequence_index") or 0)
            chapter_level = int(chapter_row.get("level") or 1)

            objectives, obj_execution = self._extract_objectives(
                source_metadata=source_metadata,
                chapter_id=chapter_id,
                chapter_title=chapter_title,
                sequence_index=sequence_index,
                segments=chapter_segments,
            )
            model = obj_execution["model"]
            provider = obj_execution.get("provider", provider)
            for key, value in obj_execution["token_usage"].items():
                token_usage[key] = token_usage.get(key, 0) + value

            salience = _chapter_salience(sequence_index, len(sorted_chapters), len(chapter_segments))
            items, execution = self._extract_chapter(
                source_metadata=source_metadata,
                chapter_id=chapter_id,
                chapter_title=chapter_title,
                sequence_index=sequence_index,
                chapter_level=chapter_level,
                segments=chapter_segments,
                objectives=objectives,
                existing_labels=existing_labels or [],
                salience=salience,
            )
            model = execution["model"]
            provider = execution.get("provider", provider)

            for key, value in execution["token_usage"].items():
                token_usage[key] = token_usage.get(key, 0) + value

            chapter_outputs.append(
                ChapterKnowledgeOutput(
                    chapter_id=chapter_id,
                    chapter_title=chapter_title,
                    sequence_index=sequence_index,
                    segment_ids=[
                        str(segment_id)
                        for segment_id in (chapter_row.get("segment_ids") or [])
                    ],
                    learning_objectives=objectives,
                    items=items,
                ),
            )
            all_objectives.extend(objectives)

        merged_items = merge_knowledge_items(
            [item for chapter in chapter_outputs for item in chapter.items],
        )

        intellex_settings = get_settings().intellex

        # Embedding-based semantic dedup across the whole document, catching
        # near-duplicates that differ in wording and that the slug merge and a
        # batched LLM consolidation pass would miss. Off unless enabled.
        if intellex_settings.extract_embedding_dedup and len(merged_items) > 1:
            embeddings = self.embedding_client.embed(
                [_dedup_text(item) for item in merged_items],
            )
            merged_items = deduplicate_by_embedding(
                merged_items,
                embeddings,
                threshold=intellex_settings.extract_embedding_similarity_threshold,
            )

        # Capture the objective↔concept linkage now, while objective_labels is
        # still reliable (consolidation can drop it), for coverage below.
        objective_slugs = objective_concept_slugs(merged_items)

        consolidated_items, consolidation_execution = self._consolidate_globally(
            source_metadata=source_metadata,
            items=merged_items,
        )
        model = consolidation_execution["model"]
        provider = consolidation_execution.get("provider", provider)
        for key, value in consolidation_execution["token_usage"].items():
            token_usage[key] = token_usage.get(key, 0) + value

        # Replace self-declared importance with a comparative, document-wide
        # ranking so the essential/supporting/contextual split stays calibrated.
        consolidated_items = calibrate_importance(
            consolidated_items,
            essential_fraction=intellex_settings.extract_essential_fraction,
            supporting_fraction=intellex_settings.extract_supporting_fraction,
        )

        # Backfill each objective's concept_labels and guarantee every objective
        # is backed by an essential concept (overrides the quantile where needed).
        chapter_objectives = [
            objective
            for chapter in chapter_outputs
            for objective in chapter.learning_objectives
        ]
        ensure_objective_coverage(consolidated_items, chapter_objectives, objective_slugs)

        for item in consolidated_items:
            item.selection_score = selection_score(item)

        # LLM "wiki editor" gate: select which entries are promoted to canonical;
        # the rest are kept as candidates (QnGen consumes only canonical).
        consolidated_items, curation_execution = self._curate_entries(
            source_metadata=source_metadata,
            items=consolidated_items,
        )
        model = curation_execution["model"]
        provider = curation_execution.get("provider", provider)
        for key, value in curation_execution["token_usage"].items():
            token_usage[key] = token_usage.get(key, 0) + value

        return ExtractChapterKnowledgeOutput(
            chapters=chapter_outputs,
            items=consolidated_items,
            learning_objectives=all_objectives,
        ), {
            "model": model,
            "provider": provider,
            "token_usage": token_usage,
            "chapter_count": len(chapter_outputs),
            "objective_count": len(all_objectives),
        }

    def _extract_objectives(
        self,
        *,
        source_metadata: dict[str, Any],
        chapter_id: str,
        chapter_title: str,
        sequence_index: int,
        segments: list[dict[str, Any]],
    ) -> tuple[list[LearningObjective], dict[str, Any]]:
        segment_batches = batch_chapter_segments_for_llm(segments)
        segments_json = segment_batches[0][0] if segment_batches else "[]"

        result = self.llm_client.complete_json(
            system_prompt=OBJECTIVES_SYSTEM_PROMPT,
            user_prompt=OBJECTIVES_USER_TEMPLATE.format(
                source_metadata=json.dumps(source_metadata, indent=2),
                chapter_id=chapter_id,
                chapter_title=chapter_title,
                sequence_index=sequence_index,
                segments_json=segments_json,
            ),
        )

        objectives: list[LearningObjective] = []
        for raw in result.content.get("objectives") or []:
            if not isinstance(raw, dict):
                continue
            try:
                objectives.append(LearningObjective.model_validate(raw))
            except Exception:
                continue

        return objectives, {
            "model": result.model,
            "provider": result.provider,
            "token_usage": result.token_usage,
        }

    def _extract_chapter(
        self,
        *,
        source_metadata: dict[str, Any],
        chapter_id: str,
        chapter_title: str,
        sequence_index: int,
        chapter_level: int,
        segments: list[dict[str, Any]],
        objectives: list[LearningObjective],
        existing_labels: list[str],
        salience: float,
    ) -> tuple[list[DeconstructedConcept], dict[str, Any]]:
        segment_batches = batch_chapter_segments_for_llm(segments)
        if salience < 0.35 and len(segment_batches) > 1:
            segment_batches = segment_batches[:1]

        chapter_segment_ids = {str(segment["id"]) for segment in segments}
        segment_text_by_id = {
            str(segment["id"]): str(segment.get("text") or "") for segment in segments
        }
        items: list[DeconstructedConcept] = []
        token_usage: dict[str, int] = {}
        model = self.llm_client.model
        provider = self.llm_client.provider
        labels = list(existing_labels)
        objectives_json = json.dumps(
            [obj.model_dump() for obj in objectives],
            indent=2,
        )

        for batch_index, (segments_json, _) in enumerate(segment_batches):
            batch_title = chapter_title
            if len(segment_batches) > 1:
                batch_title = f"{chapter_title} (part {batch_index + 1}/{len(segment_batches)})"

            result = self.llm_client.complete_json(
                system_prompt=CONCEPTS_SYSTEM_PROMPT,
                user_prompt=CONCEPTS_USER_TEMPLATE.format(
                    source_metadata=json.dumps(source_metadata, indent=2),
                    chapter_id=chapter_id,
                    chapter_title=batch_title,
                    sequence_index=sequence_index,
                    chapter_level=chapter_level,
                    objectives_json=objectives_json,
                    segments_json=segments_json,
                    existing_labels=json.dumps(labels),
                ),
            )
            model = result.model
            provider = result.provider

            for key, value in result.token_usage.items():
                token_usage[key] = token_usage.get(key, 0) + value

            raw_items = result.content.get("items") or []

            for raw in raw_items:
                if not isinstance(raw, dict):
                    continue
                concept = DeconstructedConcept.model_validate(raw)
                concept.chapter_id = chapter_id
                concept.chapter_sequence_index = sequence_index
                concept.evidence_segment_ids = [
                    segment_id
                    for segment_id in concept.evidence_segment_ids
                    if segment_id in chapter_segment_ids
                ]

                in_chapter_quotes = [
                    quote
                    for quote in concept.evidence_quotes
                    if quote.get("segment_id") in chapter_segment_ids
                ]
                quoted_segment_ids = {quote.get("segment_id") for quote in in_chapter_quotes}
                verified_quotes = [
                    quote
                    for quote in in_chapter_quotes
                    if quote_supported_by_segment(
                        str(quote.get("quote") or ""),
                        segment_text_by_id.get(str(quote.get("segment_id")), ""),
                    )
                ]
                verified_segment_ids = {quote.get("segment_id") for quote in verified_quotes}
                # Drop segments whose only grounding was an unverifiable quote;
                # keep segments cited without any quote (nothing to verify against).
                concept.evidence_segment_ids = [
                    segment_id
                    for segment_id in concept.evidence_segment_ids
                    if segment_id in verified_segment_ids or segment_id not in quoted_segment_ids
                ]
                concept.evidence_quotes = verified_quotes

                if concept.term_label and concept.definition and concept.evidence_segment_ids:
                    if concept.importance in _deep_importance_levels() or salience >= 0.35:
                        items.append(concept)
                        labels.append(concept.term_label)
                        labels.extend(concept.aliases)

            labels = sorted(set(labels))

        return merge_knowledge_items(items), {
            "model": model,
            "provider": provider,
            "token_usage": token_usage,
        }

    def _curate_entries(
        self,
        *,
        source_metadata: dict[str, Any],
        items: list[DeconstructedConcept],
    ) -> tuple[list[DeconstructedConcept], dict[str, Any]]:
        empty_execution = {
            "model": self.llm_client.model,
            "provider": self.llm_client.provider,
            "token_usage": {},
        }
        budget = get_settings().intellex.extract_max_entries_per_document

        # Gate is off (no budget) or already within budget: keep everything
        # canonical — preserves today's behavior until a budget is configured.
        if budget <= 0 or len(items) <= budget:
            for item in items:
                item.status = "canonical"
            return items, empty_execution

        candidates = [
            {
                "term_label": item.term_label,
                "entry_kind": item.entry_kind,
                "importance": item.importance,
                "evidence_segments": len(item.evidence_segment_ids),
                "has_objective": bool(item.objective_labels),
                "selection_score": round(item.selection_score or 0.0, 3),
                "definition": item.definition[:200],
            }
            for item in items
        ]

        result = self.llm_client.complete_json(
            system_prompt=CURATION_SYSTEM_PROMPT,
            user_prompt=CURATION_USER_TEMPLATE.format(
                source_metadata=json.dumps(source_metadata, indent=2),
                budget=budget,
                candidates_json=json.dumps(candidates, indent=2),
            ),
        )

        selected_labels = [str(label) for label in (result.content.get("canonical_labels") or [])]
        canonical_indices = resolve_canonical_selection(
            items,
            budget=budget,
            selected_labels=selected_labels,
        )
        for index, item in enumerate(items):
            item.status = "canonical" if index in canonical_indices else "candidate"

        return items, {
            "model": result.model,
            "provider": result.provider,
            "token_usage": result.token_usage,
        }

    def _consolidate_globally(
        self,
        *,
        source_metadata: dict[str, Any],
        items: list[DeconstructedConcept],
    ) -> tuple[list[DeconstructedConcept], dict[str, Any]]:
        if len(items) < 2:
            return items, {
                "model": self.llm_client.model,
                "provider": self.llm_client.provider,
                "token_usage": {},
            }

        token_usage: dict[str, int] = {}
        model = self.llm_client.model
        provider = self.llm_client.provider
        working = list(items)

        batches = [
            working[start : start + _CONSOLIDATION_BATCH_SIZE]
            for start in range(0, len(working), _CONSOLIDATION_BATCH_SIZE)
        ]

        for batch in batches:
            if len(batch) < 2:
                continue

            try:
                batch_result, execution = self._consolidate_batch(
                    source_metadata=source_metadata,
                    items=batch,
                )
            except RuntimeError:
                continue

            model = execution["model"]
            provider = execution.get("provider", provider)
            for key, value in execution["token_usage"].items():
                token_usage[key] = token_usage.get(key, 0) + value

            if batch_result:
                slug_to_item = {
                    (normalize_slug(item.term_label), item.entry_kind): item
                    for item in working
                }
                for consolidated in batch_result:
                    key = (normalize_slug(consolidated.term_label), consolidated.entry_kind)
                    slug_to_item[key] = consolidated
                working = list(slug_to_item.values())

        return merge_knowledge_items(working), {
            "model": model,
            "provider": provider,
            "token_usage": token_usage,
        }

    def _consolidate_batch(
        self,
        *,
        source_metadata: dict[str, Any],
        items: list[DeconstructedConcept],
    ) -> tuple[list[DeconstructedConcept], dict[str, Any]]:
        payload = [_slim_concept_for_consolidation(item) for item in items]
        result = self.llm_client.complete_json(
            system_prompt=CONSOLIDATION_SYSTEM_PROMPT,
            user_prompt=CONSOLIDATION_USER_TEMPLATE.format(
                source_metadata=json.dumps(source_metadata, indent=2),
                items_json=json.dumps(payload, indent=2),
            ),
        )

        consolidated: list[DeconstructedConcept] = []
        for raw in result.content.get("items") or []:
            if not isinstance(raw, dict):
                continue
            try:
                consolidated.append(DeconstructedConcept.model_validate(raw))
            except Exception:
                continue

        return consolidated or items, {
            "model": result.model,
            "provider": result.provider,
            "token_usage": result.token_usage,
        }


def _merge_into(existing: DeconstructedConcept, item: DeconstructedConcept) -> None:
    """Fold ``item`` into ``existing`` in place (union evidence, keep richer kind)."""
    existing.aliases = sorted({*existing.aliases, *item.aliases, item.term_label})
    existing.evidence_segment_ids = sorted(
        {*existing.evidence_segment_ids, *item.evidence_segment_ids},
    )
    existing.objective_labels = sorted({*existing.objective_labels, *item.objective_labels})

    seen_quotes = {
        (quote.get("segment_id"), quote.get("quote"))
        for quote in existing.evidence_quotes
    }
    for quote in item.evidence_quotes:
        quote_key = (quote.get("segment_id"), quote.get("quote"))
        if quote_key not in seen_quotes:
            existing.evidence_quotes.append(quote)
            seen_quotes.add(quote_key)

    if _IMPORTANCE_ORDER.get(item.importance, 0) > _IMPORTANCE_ORDER.get(existing.importance, 0):
        existing.importance = item.importance
    if item.confidence > existing.confidence:
        existing.confidence = item.confidence
    # When a term and a concept collapse together, keep the richer kind.
    existing.entry_kind = pick_entry_kind(existing.entry_kind, item.entry_kind)


def merge_knowledge_items(items: list[DeconstructedConcept]) -> list[DeconstructedConcept]:
    merged: dict[tuple[str, str], DeconstructedConcept] = {}

    for item in items:
        key = (normalize_slug(item.term_label), merge_group(item.entry_kind))
        existing = merged.get(key)

        if not existing:
            merged[key] = item.model_copy(deep=True)
            continue

        _merge_into(existing, item)

    return list(merged.values())


def _dedup_text(item: DeconstructedConcept) -> str:
    aliases = " ".join(item.aliases)
    return f"{item.term_label}. {item.definition} {aliases}".strip()


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def deduplicate_by_embedding(
    items: list[DeconstructedConcept],
    embeddings: list[list[float]],
    *,
    threshold: float,
) -> list[DeconstructedConcept]:
    """Merge near-duplicate candidates by embedding cosine similarity.

    Greedy single-link clustering across the whole document (not batched), so it
    catches semantic duplicates that differ in wording and that the slug merge
    and a batched LLM pass would miss. Only items in the same ``merge_group``
    (term/concept vs insight) are ever merged. Returns one item per cluster, in
    first-occurrence order.
    """
    if len(items) != len(embeddings) or len(items) < 2:
        return items

    total = len(items)
    assigned = [False] * total
    result: list[DeconstructedConcept] = []

    for i in range(total):
        if assigned[i]:
            continue
        representative = items[i].model_copy(deep=True)
        assigned[i] = True
        for j in range(i + 1, total):
            if assigned[j]:
                continue
            if merge_group(items[i].entry_kind) != merge_group(items[j].entry_kind):
                continue
            if _cosine_similarity(embeddings[i], embeddings[j]) >= threshold:
                _merge_into(representative, items[j])
                assigned[j] = True
        result.append(representative)

    return result
