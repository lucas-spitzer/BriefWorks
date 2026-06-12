from __future__ import annotations

from app.mathesys.audio.defaults import DEFAULT_AUDIO_FORMAT_OPTIONS
from app.mathesys.audio.models import (
    AudioDocument,
    AudioSection,
    ElevenLabsMode,
    ElevenLabsStructuredTextOutput,
    ElevenLabsVoiceSettings,
)


def _section_text_expressive(
    section: AudioSection,
    *,
    is_first: bool,
    section_pause_tag: str,
    title_pause_tag: str,
) -> str:
    parts: list[str] = []

    if not is_first:
        parts.append(section_pause_tag)

    parts.append(f"[focused] {section.title}... {title_pause_tag}")

    for paragraph in section.paragraphs:
        cleaned = paragraph.text.strip()

        if cleaned:
            parts.append(cleaned)

    for subsection in section.subsections:
        parts.append(
            _section_text_expressive(
                subsection,
                is_first=False,
                section_pause_tag=section_pause_tag,
                title_pause_tag=title_pause_tag,
            ),
        )

    return "\n".join(parts)


def _section_text_strict(
    section: AudioSection,
    *,
    is_first: bool,
) -> str:
    parts: list[str] = []

    if not is_first:
        parts.append('<break time="3.0s" />')

    parts.append(section.title)
    parts.append('<break time="1.5s" />')

    for paragraph in section.paragraphs:
        cleaned = paragraph.text.strip()

        if cleaned:
            parts.append(cleaned)

    for subsection in section.subsections:
        parts.append(_section_text_strict(subsection, is_first=False))

    return " ".join(parts)


def emit_eleven_labs_structured_text(
    document: AudioDocument,
    *,
    mode: ElevenLabsMode = "expressive_v3",
    model_id: str | None = None,
) -> ElevenLabsStructuredTextOutput:
    eleven_defaults = DEFAULT_AUDIO_FORMAT_OPTIONS["eleven_labs"]
    voice_defaults = eleven_defaults["voice_settings"]

    if mode == "expressive_v3":
        resolved_model = model_id or eleven_defaults["expressive_model"]
        section_parts = [
            _section_text_expressive(
                section,
                is_first=index == 0,
                section_pause_tag=eleven_defaults["section_pause_tag"],
                title_pause_tag=eleven_defaults["title_pause_tag"],
            )
            for index, section in enumerate(document.sections)
        ]
        text = "\n\n".join(section_parts)
        warnings = [
            "Pause timing is approximate when using eleven_v3 structured text. "
            "Validate output timing with timestamps or forced alignment.",
        ]
    else:
        resolved_model = model_id or eleven_defaults["strict_fallback_model"]
        section_parts = [
            _section_text_strict(section, is_first=index == 0)
            for index, section in enumerate(document.sections)
        ]
        text = " ".join(section_parts)
        warnings = [
            "Break tag behavior must be validated on the selected ElevenLabs model "
            "and voice. Do not assume exact timing without timestamp validation.",
        ]

    return ElevenLabsStructuredTextOutput(
        text=text,
        model_id=resolved_model,
        language_code=eleven_defaults["language_code"],
        voice_settings=ElevenLabsVoiceSettings(
            similarity_boost=voice_defaults["similarity_boost"],
            style=voice_defaults["style"],
            speed=voice_defaults["speed"],
        ),
        warnings=warnings,
    )
