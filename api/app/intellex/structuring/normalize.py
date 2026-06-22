"""Stage: NORMALIZE (llamaparse-normalize).

Flatten LlamaParse's structured `pages[].items[]` output into a single flat,
reading-order list of Elements, dropping page furniture (running headers and
footers / page numbers). Replaces the clutter-removal half of the old
prepare-document step, but does it structurally (by item type) rather than with
heuristics + an LLM call.
"""
from __future__ import annotations

import re
from typing import Any, Iterable

from app.intellex.structuring.models import FURNITURE_TYPES, Element


def _clean_text(item: dict[str, Any]) -> str:
    """Cleanest plain-text form of an item: LlamaParse `value`, else stripped md."""
    value = item.get("value")
    if isinstance(value, str) and value.strip():
        return value.strip()
    md = item.get("md") or ""
    md = re.sub(r"^\s*#{1,6}\s*", "", md)  # drop leading "# " / "## "
    return md.strip()


def normalize_structured_pages(
    pages: Iterable[dict[str, Any]],
    *,
    furniture_types: tuple[str, ...] = FURNITURE_TYPES,
) -> tuple[list[Element], dict[str, int]]:
    """Return (elements, dropped_furniture_counts).

    `pages` is the LlamaParse structured result: a list of objects each with a
    `page_number` and an `items` list of {type, md, value, level, bbox, ...}.
    """
    furniture = set(furniture_types)
    elements: list[Element] = []
    dropped: dict[str, int] = {}
    index = 0

    for page in pages:
        page_no = page.get("page_number")
        for item in page.get("items", []):
            itype = item.get("type")
            if itype in furniture:
                dropped[itype] = dropped.get(itype, 0) + 1
                continue
            elements.append(
                Element(
                    index=index,
                    page=page_no,
                    type=itype,
                    level=item.get("level"),
                    text=_clean_text(item),
                    md=item.get("md") or "",
                )
            )
            index += 1

    return elements, dropped
