from __future__ import annotations

import pytest

from app.services.llm.factory import (
    ActionOverride,
    get_llm_client,
    overrides_from_rows,
    reset_workspace_overrides,
    resolve_action,
    set_workspace_overrides,
)
from app.services.llm.model_catalog import validate_selection


@pytest.fixture(autouse=True)
def _clear_overrides():
    token = set_workspace_overrides({})
    try:
        yield
    finally:
        reset_workspace_overrides(token)


def test_workspace_override_wins_over_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_EXTRACT_KNOWLEDGE_PROVIDER", "openai")
    monkeypatch.setenv("LLM_EXTRACT_KNOWLEDGE_MODEL", "gpt-4o")

    token = set_workspace_overrides(
        {"extract_knowledge": ActionOverride(provider="anthropic", model="claude-opus-4-8")},
    )
    try:
        provider, model = resolve_action("extract_knowledge")
    finally:
        reset_workspace_overrides(token)

    assert provider == "anthropic"
    assert model == "claude-opus-4-8"


def test_resolve_falls_through_when_no_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_QNGEN_DRAFT_PROVIDER", "openai")
    monkeypatch.setenv("LLM_QNGEN_DRAFT_MODEL", "gpt-4o")

    provider, model = resolve_action("qngen_draft")

    assert provider == "openai"
    assert model == "gpt-4o"


def test_get_llm_client_honors_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    token = set_workspace_overrides(
        {"source_research": ActionOverride(provider="openai", model="gpt-5.4")},
    )
    try:
        client = get_llm_client("source_research")
    finally:
        reset_workspace_overrides(token)

    assert client.provider == "openai"
    assert client.model == "gpt-5.4"


def test_overrides_from_rows_builds_map_and_normalizes() -> None:
    rows = [
        {"stage_action": "prepare", "provider": "OpenAI", "model": "gpt-5.4-mini"},
        {"stage_action": "extract_knowledge", "provider": "anthropic", "model": "claude-sonnet-4-6"},
    ]

    overrides = overrides_from_rows(rows)

    assert overrides["prepare"] == ActionOverride(provider="openai", model="gpt-5.4-mini")
    assert overrides["extract_knowledge"].model == "claude-sonnet-4-6"


def test_overrides_from_rows_drops_unbuildable_or_empty() -> None:
    rows = [
        {"stage_action": "prepare", "provider": "google", "model": "gemini-3"},
        {"stage_action": "", "provider": "openai", "model": "gpt-4o"},
        {"stage_action": "extract_knowledge", "provider": "anthropic", "model": ""},
    ]

    assert overrides_from_rows(rows) == {}


def test_overrides_from_rows_allows_uncatalogued_model() -> None:
    rows = [{"stage_action": "prepare", "provider": "openai", "model": "gpt-6-future"}]

    overrides = overrides_from_rows(rows)

    assert overrides["prepare"] == ActionOverride(provider="openai", model="gpt-6-future")


def test_validate_selection_accepts_known_and_unknown_models() -> None:
    assert validate_selection("anthropic", "claude-opus-4-8") is None
    # A model not yet in the catalog is still selectable.
    assert validate_selection("openai", "gpt-6-future") is None


def test_validate_selection_rejects_bad_input() -> None:
    assert validate_selection("google", "gemini-3") is not None
    assert validate_selection("openai", "") is not None
    # Known model paired with the wrong provider is rejected.
    assert validate_selection("openai", "claude-opus-4-8") is not None
