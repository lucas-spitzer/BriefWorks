from __future__ import annotations

import pytest

from app.artifact_paths import (
    downloadable_artifact_path,
    is_type_nested_artifact_path,
    needs_type_nesting,
)


def test_downloadable_artifact_path_nests_by_type() -> None:
    source = "workspaces/ws-1/sources/src-1/warfighting.pdf"
    assert downloadable_artifact_path(
        source, "electronic_book", "art-1", "warfighting.epub"
    ) == "workspaces/ws-1/sources/src-1/artifacts/ebook/art-1/warfighting.epub"
    assert downloadable_artifact_path(
        source, "narration_audio", "art-2", "warfighting-narration.json"
    ) == (
        "workspaces/ws-1/sources/src-1/artifacts/narration/art-2/"
        "warfighting-narration.json"
    )
    assert downloadable_artifact_path(
        source, "wiki_json", "art-3", "warfighting-wiki.json"
    ) == "workspaces/ws-1/sources/src-1/artifacts/wiki/art-3/warfighting-wiki.json"


def test_downloadable_artifact_path_rejects_unknown_type() -> None:
    with pytest.raises(ValueError, match="Unknown artifact type"):
        downloadable_artifact_path(
            "workspaces/ws-1/sources/src-1/file.pdf",
            "web_explainer",
            "art-1",
            "page.html",
        )


def test_is_type_nested_artifact_path() -> None:
    nested = (
        "workspaces/ws-1/sources/src-1/artifacts/ebook/art-1/warfighting.epub"
    )
    old = "workspaces/ws-1/sources/src-1/artifacts/art-1/warfighting.epub"
    voice = (
        "workspaces/ws-1/sources/src-1/artifacts/"
        "4YYIPFI9wE5c4L2eu2Gb/00020fe1-0c01-4e06-a23e-aaaaaaaaaaaa.mp3"
    )
    assert is_type_nested_artifact_path(nested) is True
    assert is_type_nested_artifact_path(old) is False
    assert is_type_nested_artifact_path(voice) is False


def test_needs_type_nesting_skips_voice_id_dumps() -> None:
    old_uuid = (
        "workspaces/ws-1/sources/src-1/artifacts/"
        "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/warfighting.epub"
    )
    nested = (
        "workspaces/ws-1/sources/src-1/artifacts/ebook/"
        "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/warfighting.epub"
    )
    voice = (
        "workspaces/ws-1/sources/src-1/artifacts/"
        "4YYIPFI9wE5c4L2eu2Gb/00020fe1-0c01-4e06-a23e-aaaaaaaaaaaa.mp3"
    )
    pending = "pending"
    assert needs_type_nesting(old_uuid) is True
    assert needs_type_nesting(nested) is False
    assert needs_type_nesting(voice) is False
    assert needs_type_nesting(pending) is False
