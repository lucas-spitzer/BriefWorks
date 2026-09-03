# LLM Reasoning Levels — Provider Guide & Foundry Integration Plan

This document describes how to control reasoning / thinking depth across LLM providers, and how Foundry should wire those controls through configuration and client code.

Use this as the reference when implementing reasoning-level support in `api/app/config.py` and the provider clients under `api/app/services/llm/`.

---

## Terminology

| Term | Meaning |
|------|---------|
| **Reasoning tokens** | Hidden internal tokens the model spends "thinking" before producing visible output. Billed separately on most providers. |
| **Reasoning effort** | A coarse dial (e.g. `low`, `medium`, `high`) that guides how much reasoning the model performs. Provider-native on OpenAI and newer Anthropic models. |
| **Thinking budget** | A token cap on reasoning. Legacy on Anthropic 4.6+; still primary on Gemini 2.5 and older Anthropic models. |
| **Adaptive thinking** | The model decides dynamically whether and how much to think. Anthropic's recommended mode for Sonnet 4.6+ and Opus 4.6+. |

Reasoning controls affect **latency, cost, and quality**. Higher effort improves complex tasks but is wasteful for simple JSON extraction.

---

## Current Foundry State

As of this writing, Foundry **does not expose reasoning controls**. Model selection is configurable; reasoning depth is not.

| Call site | Client | Model env var | Reasoning control |
|-----------|--------|---------------|-------------------|
| `source-research` | `OpenAIClient` | `SOURCE_RESEARCH_MODEL` | None (Chat Completions, no `reasoning` param) |
| `prepare` | `OpenAIClient` | — (removed) | None |
| `extract-knowledge` | `AnthropicClient` via factory | — (removed) | None |
| QnGen draft / critique | factory | `DRAFT_MODEL`, `CRITIQUE_MODEL` | None |

Relevant code today:

- OpenAI: `api/app/services/openai_client.py` — `chat.completions.create` with `response_format: json_object`
- Anthropic: `api/app/services/llm/anthropic_client.py` — `messages.create` with `model`, `max_tokens`, `system`, `messages`
- Routing: `api/app/config.py` — dedicated per-action model env vars (`SOURCE_RESEARCH_MODEL`, `DRAFT_MODEL`, …)

---

## Proposed Foundry Configuration

When implemented, use **provider-specific env vars** with optional **per-action overrides**. Reasoning semantics differ too much across providers for a single universal enum.

### Global defaults (`.env`)

```bash
# OpenAI — used by source-research, wiki structuring, reader define, qngen draft
SOURCE_RESEARCH_MODEL=gpt-5.4-mini
WIKI_STRUCTURING_MODEL=gpt-5.4
READER_DEFINE_MODEL=gpt-5.4-mini
DRAFT_MODEL=gpt-5.4-mini
OPENAI_REASONING_EFFORT=medium          # none | minimal | low | medium | high | xhigh

# Anthropic — used by extract-knowledge, qngen draft/critique
ANTHROPIC_MAX_TOKENS=16384
ANTHROPIC_THINKING_MODE=adaptive        # off | adaptive | manual
ANTHROPIC_THINKING_EFFORT=medium        # low | medium | high | max (adaptive mode)
ANTHROPIC_THINKING_BUDGET_TOKENS=0      # manual mode only; 0 = disabled
```

### Per-action overrides (optional)

Follow the existing `LLM_<ACTION>_*` pattern:

```bash
LLM_QNGEN_CRITIQUE_REASONING_EFFORT=high
LLM_EXTRACT_KNOWLEDGE_THINKING_EFFORT=low
```

Resolution order: **action override → provider global default → provider/model default**.

### Normalized internal shape

Provider clients should accept a small internal struct, e.g.:

```python
@dataclass(frozen=True)
class ReasoningSettings:
    effort: str | None = None           # provider-mapped enum
    thinking_mode: str | None = None    # anthropic: off | adaptive | manual
    thinking_budget_tokens: int | None = None
```

Each client translates this into its native API parameters. Stages and the `LLMClient` protocol stay provider-agnostic.

---

## OpenAI

### Which API to use

| API | Reasoning param | Structured JSON | Recommendation |
|-----|-----------------|-----------------|----------------|
| **Responses API** | `reasoning: { effort: "..." }` | `text.format` with JSON schema | **Preferred** for GPT-5.x and o-series |
| **Chat Completions** | `reasoning_effort: "..."` (top-level) | `response_format: { type: "json_object" }` | Works but limited; OpenAI recommends Responses for reasoning models |

Foundry currently uses Chat Completions. Migrating `OpenAIClient` to Responses is the main engineering task for proper GPT-5.4 support.

### Effort levels

Supported values are **model-dependent**. Common set:

| Effort | When to use |
|--------|-------------|
| `none` | No reasoning; fastest. Supported on some GPT-5.1+ variants. |
| `minimal` | Near-zero reasoning; good for classification, formatting, short extraction. |
| `low` | Light reasoning; good latency/cost balance for structured extraction. |
| `medium` | Default for most GPT-5.x workloads. |
| `high` | Complex multi-step tasks, critique passes, agentic workflows. |
| `xhigh` | Deepest reasoning; newer codex/max-tier models only. |

Defaults vary by model (e.g. GPT-5.5 defaults to `medium`; some GPT-5.1 variants default to `none`). Pin model snapshots in production.

### Responses API example (target implementation)

```python
from openai import OpenAI

client = OpenAI()

response = client.responses.create(
    model="gpt-5.4",
    reasoning={"effort": "low"},
    instructions=system_prompt,
    input=user_prompt,
    text={
        "format": {"type": "json_object"},
    },
)

# Parse JSON from response.output_text or walk response.output
```

### Chat Completions example (current path, add effort)

```python
response = client.chat.completions.create(
    model="gpt-5.4",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ],
    response_format={"type": "json_object"},
    reasoning_effort="low",
)
```

### OpenAI caveats for Foundry

1. **Output parsing** — Responses return an `output` array (messages, tool calls, reasoning summaries). Do not assume text is at `output[0]`. Use `response.output_text` when available.
2. **Reasoning token billing** — Reasoning tokens appear in usage metadata. Extend `api/app/services/api_pricing.py` if reasoning tokens are priced differently.
3. **Structured output** — Prefer JSON schema via Responses `text.format` over free-form `json_object` when migrating.
4. **Role names** — Responses uses `instructions` + `input` (or `developer` / `user` roles), not always `system`.

### Suggested Foundry defaults (OpenAI stages)

| Stage | Suggested effort | Rationale |
|-------|------------------|-----------|
| `source-research` | `low` | Structured bibliographic extraction from labeled slices; speed matters. |
| `prepare` | `low`–`medium` | Content filtering and restructuring; moderate complexity. |

---

## Anthropic

Anthropic has gone through two generations of thinking controls. **Model ID determines which API shape is valid.**

### Mode matrix by model family

| Model family | Recommended config | Deprecated / rejected |
|--------------|-------------------|------------------------|
| **Sonnet 4.6, Opus 4.6** | `thinking: { type: "adaptive" }` + `output_config: { effort: "..." }` | `budget_tokens` deprecated; still accepted temporarily |
| **Opus 4.7, Opus 4.8** | Adaptive only | `thinking: { type: "enabled", budget_tokens: N }` → **400 error** |
| **Fable 5, Mythos 5** | Thinking always on; use `output_config.effort` only | Cannot disable thinking |
| **Haiku 4.5, Sonnet 4.5, Opus 4.5** | `thinking: { type: "enabled", budget_tokens: N }` | No adaptive mode |

### Adaptive thinking + effort (Sonnet 4.6+)

```python
from anthropic import Anthropic

client = Anthropic()

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=16384,
    system=system_prompt,
    messages=[{"role": "user", "content": user_prompt}],
    thinking={"type": "adaptive"},
    output_config={"effort": "medium"},
)
```

Effort values: `low`, `medium`, `high`, `max` (and `xhigh` on some Opus variants). At `high` / `max`, Claude almost always thinks deeply. At `low`, it may skip thinking on simple prompts.

**Important:** `effort` goes in `output_config`, **not** inside `thinking`. Putting it in the wrong object returns a validation error.

### Manual thinking budget (Haiku 4.5 and older)

```python
response = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=16384,
    system=system_prompt,
    messages=[{"role": "user", "content": user_prompt}],
    thinking={"type": "enabled", "budget_tokens": 8000},
)
```

Rules:

- `budget_tokens` must be less than `max_tokens`.
- Minimum budget varies by model (often 1024+).
- Set `thinking: { type: "disabled" }` or omit thinking to turn off (where supported).

### Anthropic caveats for Foundry

1. **JSON prefill** — `AnthropicClient` uses assistant prefill `{"` for structured JSON. Extended thinking may interact with prefill; test per model. Prefill is already disabled for some models (see `_PREFILL_UNSUPPORTED_MODELS`).
2. **Temperature** — Some Opus 4.8+ models reject non-default `temperature` / `top_p` when thinking is enabled.
3. **Output parsing** — Thinking blocks appear in `content` with `type: "thinking"`. Extract only `type: "text"` blocks for JSON parsing.
4. **Token usage** — Billing includes thinking tokens separately from output tokens in some cases; normalize in `LLMCompletionResult.token_usage`.

### Suggested Foundry defaults (Anthropic stages)

| Stage | Suggested config | Rationale |
|-------|------------------|-----------|
| `extract-knowledge` | adaptive + `effort: low` | High volume, structured extraction per concept batch. |
| `qngen_draft` | adaptive + `effort: medium` | Creative generation benefits from moderate reasoning. |
| `qngen_critique` | adaptive + `effort: high` | Quality gate; worth extra latency and cost. |

---

## Google Gemini (future provider)

Foundry does not use Gemini today. Include for factory extensibility.

### Gemini 2.5 — `thinking_budget` (tokens)

```python
from google import genai
from google.genai import types

client = genai.Client()

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=user_prompt,
    config=types.GenerateContentConfig(
        system_instruction=system_prompt,
        thinking_config=types.ThinkingConfig(
            thinking_budget=1024,   # 0 = off (where supported), -1 = dynamic
        ),
    ),
)
```

| Model | Disable thinking | Dynamic thinking |
|-------|------------------|------------------|
| 2.5 Pro | Not supported | `thinking_budget=-1` (default) |
| 2.5 Flash | `thinking_budget=0` | `thinking_budget=-1` |
| 2.5 Flash Lite | `0` or omit (off by default) | `-1` |

### Gemini 3.x — `thinking_level` (enum)

```python
thinking_config=types.ThinkingConfig(thinking_level="medium")
```

Levels: `minimal`, `low`, `medium`, `high`. `thinking_budget` is accepted for backward compatibility but **not recommended** on 3.x.

### Proposed env vars (if Gemini is added)

```bash
GEMINI_THINKING_MODE=level          # off | budget | level | dynamic
GEMINI_THINKING_LEVEL=medium
GEMINI_THINKING_BUDGET_TOKENS=0
```

---

## Provider Comparison

| Provider | Primary control | Disable reasoning | Structured JSON | Foundry client |
|----------|----------------|-------------------|-----------------|-------------------|
| OpenAI GPT-5.x | `reasoning.effort` (Responses) or `reasoning_effort` (Chat) | `none` / `minimal` (model-dependent) | JSON schema via Responses | `OpenAIClient` |
| Anthropic 4.6+ | `thinking.type=adaptive` + `output_config.effort` | `effort: low` or omit adaptive on some models | Assistant prefill + parse | `AnthropicClient` |
| Anthropic 4.5 / Haiku | `thinking.budget_tokens` | omit thinking or `type: disabled` | Assistant prefill + parse | `AnthropicClient` |
| Google Gemini 2.5 | `thinking_budget` (int) | `0` where supported | `response_schema` | Not implemented |
| Google Gemini 3.x | `thinking_level` (enum) | `minimal` (cannot fully disable on some models) | `response_schema` | Not implemented |

There is **no safe cross-provider enum**. Map a Foundry `effort` hint per provider inside each client.

---

## Implementation Checklist

When wiring this into Foundry:

- [ ] Add `ReasoningSettings` (or equivalent) to `api/app/config.py` with global + per-action resolution.
- [ ] Extend `LLMSettings` dataclass; document vars in `api/README.md`.
- [ ] **OpenAI**: migrate `OpenAIClient.complete_json` to Responses API; pass `reasoning.effort`; update output parsing.
- [ ] **Anthropic**: branch on model family in `AnthropicClient._create_response`:
  - 4.6+ → adaptive + `output_config.effort`
  - 4.5 / Haiku → manual `budget_tokens` when `ANTHROPIC_THINKING_MODE=manual`
  - Opus 4.7+ → reject manual mode at config load time
- [ ] Filter `thinking` blocks from response content before JSON parse.
- [ ] Pass reasoning settings through `get_llm_client` / factory (clients read from settings, not env directly).
- [ ] Update `api/app/services/api_pricing.py` for reasoning/thinking token line items if needed.
- [ ] Add tests in `api/tests/test_llm_client.py` for effort param forwarding and model-family branching.
- [ ] Log resolved reasoning settings at stage start (without prompts) for debugging cost/latency.

### Client translation pseudocode

```python
def _openai_reasoning_kwargs(settings: ReasoningSettings) -> dict:
    if not settings.effort:
        return {}
    return {"reasoning": {"effort": settings.effort}}


def _anthropic_reasoning_kwargs(model: str, settings: ReasoningSettings) -> dict:
    if settings.thinking_mode == "off":
        return {}
    if _supports_adaptive(model):
        kwargs = {"thinking": {"type": "adaptive"}}
        if settings.effort:
            kwargs["output_config"] = {"effort": settings.effort}
        return kwargs
    if settings.thinking_mode == "manual" and settings.thinking_budget_tokens:
        return {
            "thinking": {
                "type": "enabled",
                "budget_tokens": settings.thinking_budget_tokens,
            }
        }
    return {}
```

---

## Operational Guidance

### Tuning workflow

1. Start at provider defaults (`medium` for both OpenAI GPT-5.x and Anthropic adaptive).
2. Run a production-like stage on a small source sample; record latency, token usage, and output quality.
3. Lower effort for high-volume extraction stages first (`source-research`, `extract-knowledge`).
4. Raise effort only on quality gates (`qngen_critique`).
5. Pin model version strings (e.g. `claude-sonnet-4-6-20250514`) when satisfied.

### Cost and latency

- Reasoning tokens are often billed at output-token rates but can dominate spend on `high` / `max`.
- Worker job timeouts (`PRODUCTION_RUN_JOB_TIMEOUT`) may need increasing if critique passes move to `high` effort on large batches.
- QnGen runs two LLM passes (draft + critique) per batch — effort changes multiply.

### When *not* to enable reasoning

- Simple JSON field extraction with strong prompts and schema validation.
- High-throughput batch stages where Haiku-class models at `low` effort are sufficient.
- Stages where output is deterministic (reformatting, slicing) — reasoning adds cost without benefit.

---

## References

### Vendor docs (also mirrored under `docs/external/` where noted)

- [OpenAI — Reasoning models](https://developers.openai.com/api/docs/guides/reasoning)
- [OpenAI — Migrate to Responses API](https://developers.openai.com/api/docs/guides/migrate-to-responses)
- [OpenAI — Text generation](https://developers.openai.com/api/docs/guides/text) (see `docs/external/openai/text-generation.md`)
- [Anthropic — Adaptive thinking](https://platform.claude.com/docs/en/build-with-claude/adaptive-thinking)
- [Anthropic — Effort parameter](https://platform.claude.com/docs/en/build-with-claude/effort)
- [Anthropic — Model migration guide](https://platform.claude.com/docs/en/about-claude/models/migration-guide)
- [Google — Gemini thinking](https://ai.google.dev/gemini-api/docs/thinking)

### Foundry code

- `api/app/config.py` — env resolution, `LLM_ACTION_DEFAULTS`
- `api/app/services/openai_client.py` — OpenAI Chat Completions (migration target)
- `api/app/services/llm/anthropic_client.py` — Anthropic Messages API
- `api/app/services/llm/factory.py` — provider routing
- `api/app/services/api_pricing.py` — token rate tables
