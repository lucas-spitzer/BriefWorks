from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from app.mathesys.audio.defaults import SPEECHIFY_SSML_CHARACTER_LIMIT
from app.mathesys.audio.emitters.speechify_ssml import SUPPORTED_SSML_TAGS
from app.mathesys.audio.models import SpeechifySsmlOutput, ValidationResult


def validate_ssml(output: SpeechifySsmlOutput) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = list(output.warnings)
    ssml = output.ssml.strip()

    if ssml.startswith("```"):
        errors.append("SSML must not contain Markdown fences.")

    if not ssml.startswith("<speak>") or not ssml.endswith("</speak>"):
        errors.append("SSML must contain exactly one root speak element.")

    speak_open = ssml.count("<speak>")
    speak_close = ssml.count("</speak>")

    if speak_open != 1 or speak_close != 1:
        errors.append("SSML must contain exactly one root speak element.")

    try:
        ET.fromstring(ssml)
    except ET.ParseError as exc:
        errors.append(f"SSML is not valid XML: {exc}")

    unsupported = re.findall(r"</?([a-zA-Z0-9:_-]+)", ssml)
    for tag in unsupported:
        local_name = tag.split(":")[-1].lower()

        if local_name not in SUPPORTED_SSML_TAGS:
            errors.append(f"Unsupported SSML tag: {local_name}")

    title_count = len(re.findall(r'<emphasis level="moderate">', ssml))
    title_pause_count = len(re.findall(r'<break time="1\.5s"/>', ssml))
    section_pause_count = len(re.findall(r'<break time="3\.0s"/>', ssml))

    if title_count and title_pause_count < title_count:
        errors.append("Every section title must be followed by a 1.5 second break.")

    if title_count > 1 and section_pause_count < title_count - 1:
        errors.append("Every section transition must include a 3.0 second break.")

    if len(ssml) > SPEECHIFY_SSML_CHARACTER_LIMIT:
        errors.append(
            f"SSML exceeds Speechify API character limit ({SPEECHIFY_SSML_CHARACTER_LIMIT}).",
        )

    return ValidationResult(
        valid=not errors,
        errors=errors,
        warnings=warnings,
    )
