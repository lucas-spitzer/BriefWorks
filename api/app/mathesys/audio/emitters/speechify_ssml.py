from __future__ import annotations

import html
import re

from app.mathesys.audio.defaults import SPEECHIFY_SSML_CHARACTER_LIMIT
from app.mathesys.audio.models import AudioDocument, AudioSection, SpeechifySsmlOutput

SUPPORTED_SSML_TAGS = frozenset(
    {
        "speak",
        "p",
        "break",
        "emphasis",
        "sub",
        "prosody",
    },
)


def _escape_xml(text: str) -> str:
    return html.escape(text, quote=False)


def _paragraph_ssml(text: str) -> str:
    return f"<p>{_escape_xml(text.strip())}</p>"


def _section_ssml(
    section: AudioSection,
    *,
    is_first: bool,
) -> tuple[str, int]:
    parts: list[str] = []
    section_count = 1

    if not is_first:
        parts.append('<break time="3.0s"/>')

    parts.append(f'<emphasis level="moderate">{_escape_xml(section.title)}</emphasis>')
    parts.append('<break time="1.5s"/>')

    for paragraph in section.paragraphs:
        cleaned = paragraph.text.strip()

        if cleaned:
            parts.append(_paragraph_ssml(cleaned))

    for subsection in section.subsections:
        nested, nested_count = _section_ssml(subsection, is_first=False)
        parts.append(nested)
        section_count += nested_count

    return "".join(parts), section_count


def emit_speechify_ssml(document: AudioDocument) -> SpeechifySsmlOutput:
    body_parts: list[str] = []
    section_count = 0

    for index, section in enumerate(document.sections):
        section_ssml, count = _section_ssml(section, is_first=index == 0)
        body_parts.append(section_ssml)
        section_count += count

    ssml = f"<speak>{''.join(body_parts)}</speak>"
    warnings: list[str] = []

    if len(ssml) > SPEECHIFY_SSML_CHARACTER_LIMIT:
        warnings.append(
            f"SSML character count ({len(ssml)}) exceeds Speechify API limit "
            f"({SPEECHIFY_SSML_CHARACTER_LIMIT}).",
        )

    return SpeechifySsmlOutput(
        ssml=ssml,
        section_count=section_count,
        estimated_character_count=len(ssml),
        warnings=warnings,
    )


def count_ssml_sections(ssml: str) -> int:
    return len(re.findall(r'<emphasis level="moderate">', ssml))
