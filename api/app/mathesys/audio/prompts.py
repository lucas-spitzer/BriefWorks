"""Prompt templates for optional LLM-assisted narration helpers.

Prepared NDR segments are already narration-ready before Mathesys runs. Mathesys
emitters must preserve heading and body text verbatim; do not re-apply content
cleaning or rewrite prose at this stage.
"""

NARRATION_PASSTHROUGH_POLICY = """TEXT FIDELITY POLICY (mandatory):
Prepared source segments have already been filtered for audio narration upstream.
Preserve every heading and body paragraph exactly as provided.
Do not omit, summarize, paraphrase, expand, or normalize wording.
You may only add non-spoken delivery wrappers required by the target format
(for example SSML speak/p/break tags or ElevenLabs pause tags outside the
source text)."""

# Retained for reference if a future optional helper needs LLM assistance.
CANONICAL_AUDIO_DOCUMENT_SYSTEM_PROMPT = """You structure already-prepared narration segments for TTS emitters.

{narration_policy}

Return only valid JSON matching the provided AudioDocument schema.""".format(
    narration_policy=NARRATION_PASSTHROUGH_POLICY,
)

CANONICAL_AUDIO_DOCUMENT_USER_TEMPLATE = """Structure this extracted content into AudioDocument JSON.

Source type: {source_type}
Language: {language}
Audience: {audience}

Canonical wiki entries (metadata only — do not rewrite body text to match):
{wiki_entries}

Chapter title: {chapter_title}

Extracted content (preserve text verbatim):
{extracted_text}

Return JSON with section, glossary, segment_ids_used, and wiki_ids_cited."""

SPEECHIFY_APP_EPUB_SYSTEM_PROMPT = """Convert structured document sections into EPUB-ready XHTML for Speechify import.

{narration_policy}

Use h1/h2/h3 for headings and p for paragraphs. Preserve heading and paragraph
text exactly. Do not add SSML or pause markers.""".format(
    narration_policy=NARRATION_PASSTHROUGH_POLICY,
)

ELEVENREADER_APP_EPUB_SYSTEM_PROMPT = """Convert structured document sections into EPUB-ready XHTML for ElevenReader import.

{narration_policy}

Use h1 for chapter headings, h2/h3 for nested headings, and p for paragraphs.
Preserve heading and paragraph text exactly.""".format(
    narration_policy=NARRATION_PASSTHROUGH_POLICY,
)

SPEECHIFY_API_SSML_SYSTEM_PROMPT = """Convert structured document sections into valid Speechify SSML.

{narration_policy}

Wrap output in one speak element. Use emphasis for section titles and break
tags for pauses between sections. Escape XML-sensitive characters in the source
text without changing the spoken words.""".format(
    narration_policy=NARRATION_PASSTHROUGH_POLICY,
)

ELEVENLABS_EXPRESSIVE_SYSTEM_PROMPT = """Convert structured document sections into ElevenLabs expressive narration text.

{narration_policy}

Add [short pause] and [long pause] tags only as delivery wrappers between
sections. Do not alter the source heading or paragraph strings.""".format(
    narration_policy=NARRATION_PASSTHROUGH_POLICY,
)

ELEVENLABS_STRICT_PAUSE_SYSTEM_PROMPT = """Convert structured document sections into ElevenLabs text with SSML break tags.

{narration_policy}

Insert break tags only as delivery wrappers between sections. Do not alter the
source heading or paragraph strings.""".format(
    narration_policy=NARRATION_PASSTHROUGH_POLICY,
)
