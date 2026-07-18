from __future__ import annotations

from typing import Any

from app.intellex.stages.models import SourceResearchOutput, WebEnrichmentOutput


def merge_research_into_source_metadata(
    existing_metadata: dict[str, Any] | None,
    research: SourceResearchOutput,
    *,
    researched_at: str,
) -> dict[str, Any]:
    metadata = dict(existing_metadata or {})
    metadata["research"] = research.to_metadata(researched_at=researched_at)
    return metadata


# Research fields the web pass may fill when the document didn't provide them.
_WEB_FILLABLE_FIELDS = ("publication_date_public", "source_url")


def merge_web_enrichment_into_source_metadata(
    existing_metadata: dict[str, Any] | None,
    enrichment: WebEnrichmentOutput,
    *,
    enriched_at: str,
) -> dict[str, Any]:
    """Layer web-verified facts onto the research block.

    Web values fill nulls only; document-extracted values win on conflict, and
    disagreements are recorded on the enrichment block instead of overwritten.
    """
    metadata = dict(existing_metadata or {})
    research = dict(metadata.get("research") or {})
    enrichment_meta = enrichment.to_metadata(enriched_at=enriched_at)

    conflicts: list[dict[str, str]] = []
    web_values = {
        "publication_date_public": enrichment.publication_date_public,
        "source_url": enrichment.canonical_url,
    }

    provenance = dict(research.get("provenance") or {})
    confidence = dict(research.get("confidence") or {})

    for field in _WEB_FILLABLE_FIELDS:
        web_value = web_values[field]
        if not web_value:
            continue

        current = research.get(field)
        if not current:
            research[field] = web_value
            provenance[field] = "web"
            field_confidence = enrichment.confidence.get(
                field if field != "source_url" else "canonical_url",
            )
            if field_confidence is not None:
                confidence[field] = field_confidence
        elif str(current) != str(web_value):
            conflicts.append(
                {
                    "field": field,
                    "document_value": str(current),
                    "web_value": str(web_value),
                },
            )

    # Corrections are advisory: recorded as conflicts, never applied silently.
    for field, corrected in enrichment.corrections.items():
        current = research.get(field)
        if current and str(current) != corrected:
            conflicts.append(
                {
                    "field": str(field),
                    "document_value": str(current),
                    "web_value": corrected,
                },
            )

    existing_sources = research.get("web_sources")
    merged_sources = list(existing_sources) if isinstance(existing_sources, list) else []
    seen_urls = {
        str(item.get("url"))
        for item in merged_sources
        if isinstance(item, dict) and item.get("url")
    }
    for source in enrichment.web_sources:
        if source.url not in seen_urls:
            merged_sources.append(source.model_dump())
            seen_urls.add(source.url)
    research["web_sources"] = merged_sources

    research["provenance"] = provenance
    research["confidence"] = confidence

    enrichment_meta["conflicts"] = conflicts
    metadata["research"] = research
    metadata["web_enrichment"] = enrichment_meta
    return metadata
