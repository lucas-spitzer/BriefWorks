"""Canonical registry of every LLM-calling pipeline stage ("action").

Single source of truth for the default provider/model of each stage that calls
an LLM. Lives at app top level (not under app.services.llm) to avoid an import
cycle with app.config, mirroring app.llm_defaults.

Runtime resolution order (see app.config._resolve_llm_action):
action env override -> provider global default -> registry default below.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.llm_defaults import GPT_54_MINI_MODEL, GPT_54_MODEL, HAIKU_45_MODEL


@dataclass(frozen=True)
class LLMAction:
    key: str
    label: str
    provider: str
    model: str


LLM_ACTIONS: tuple[LLMAction, ...] = (
    LLMAction("source_research", "Source Research", "openai", GPT_54_MINI_MODEL),
    # Needs a provider/model with server-side web search support.
    LLMAction("source_web_enrichment", "Source Web Enrichment", "anthropic", HAIKU_45_MODEL),
    LLMAction("prepare", "Prepare Document", "openai", GPT_54_MODEL),
    LLMAction("wiki_structuring", "Wiki Structuring", "openai", GPT_54_MODEL),
    LLMAction("qngen_draft", "Assessment Draft", "openai", GPT_54_MINI_MODEL),
    LLMAction("qngen_critique", "Assessment Critique", "anthropic", HAIKU_45_MODEL),
)

LLM_ACTION_DEFAULTS: dict[str, tuple[str, str]] = {
    action.key: (action.provider, action.model) for action in LLM_ACTIONS
}

LLM_GLOBAL_DEFAULT: tuple[str, str] = ("anthropic", HAIKU_45_MODEL)
