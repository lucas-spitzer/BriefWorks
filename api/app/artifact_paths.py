"""Storage paths for downloadable Mathesys artifacts in the sources bucket.

Working pipeline files stay in sibling folders (`parse/`, `structure/`,
`narration/{voice_id}/`). Exports live under `artifacts/{type}/{artifact_id}/`.
"""

from __future__ import annotations

import uuid

ARTIFACT_TYPE_FOLDERS = {
    "electronic_book": "ebook",
    "narration_audio": "narration",
    "wiki_json": "wiki",
}

_TYPE_FOLDER_SET = frozenset(ARTIFACT_TYPE_FOLDERS.values())


def artifact_type_folder(artifact_type: str) -> str:
    try:
        return ARTIFACT_TYPE_FOLDERS[artifact_type]
    except KeyError as exc:
        raise ValueError(f"Unknown artifact type: {artifact_type}") from exc


def downloadable_artifact_path(
    source_storage_path: str,
    artifact_type: str,
    artifact_id: str,
    filename: str,
) -> str:
    parent = source_storage_path.rsplit("/", 1)[0]
    folder = artifact_type_folder(artifact_type)
    return f"{parent}/artifacts/{folder}/{artifact_id}/{filename}"


def is_type_nested_artifact_path(storage_path: str) -> bool:
    """True when path is .../sources/{id}/artifacts/{type}/{artifact_id}/{file}."""
    parts = _source_artifact_parts(storage_path)
    if parts is None or len(parts) < 3:
        return False
    return parts[0] in _TYPE_FOLDER_SET


def needs_type_nesting(storage_path: str) -> bool:
    """True for .../sources/{id}/artifacts/{uuid}/{file} without a type folder.

    Voice-id dumps (non-UUID folders under artifacts/) are left alone.
    """
    if is_type_nested_artifact_path(storage_path):
        return False
    parts = _source_artifact_parts(storage_path)
    if parts is None or len(parts) < 2:
        return False
    return _looks_like_uuid(parts[0])


def _source_artifact_parts(storage_path: str) -> list[str] | None:
    """Segments after .../sources/{source_id}/artifacts/, or None."""
    parts = storage_path.split("/")
    try:
        sources_idx = parts.index("sources")
    except ValueError:
        return None
    artifacts_idx = sources_idx + 2
    if artifacts_idx >= len(parts) or parts[artifacts_idx] != "artifacts":
        return None
    return parts[artifacts_idx + 1 :]


def _looks_like_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
    except ValueError:
        return False
    return True
