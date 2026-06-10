from __future__ import annotations

import re
import unicodedata


def normalize_slug(label: str) -> str:
    normalized = unicodedata.normalize("NFKD", label)
    ascii_label = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_label.lower()).strip("-")
    return slug or "term"
