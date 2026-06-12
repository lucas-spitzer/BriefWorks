from __future__ import annotations

import re

from app.mathesys.audio.models import ElevenLabsStructuredTextOutput, ValidationResult


def validate_eleven_labs_text(output: ElevenLabsStructuredTextOutput) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = list(output.warnings)
    text = output.text
    model_id = output.model_id

    if model_id == "eleven_v3":
        if re.search(r"<break\s+time=", text, flags=re.IGNORECASE):
            errors.append("eleven_v3 output must not contain SSML break tags.")

        if "[long pause]" not in text and len(text) > 200:
            warnings.append("Expected [long pause] tags for section transitions in v3 mode.")

        if re.search(r"\[(?:focused|thoughtful|serious|long pause|short pause)\]", text):
            tag_count = len(
                re.findall(
                    r"\[(?:focused|thoughtful|serious|long pause|short pause)\]",
                    text,
                ),
            )

            if tag_count > 20:
                warnings.append("Emotional or pause tags may be overused.")

    else:
        if "[long pause]" in text or "[short pause]" in text:
            errors.append("Strict pause fallback mode must not use expressive pause tags.")

        if "<break time=\"3.0s\"" not in text and "<break time='3.0s'" not in text:
            warnings.append("Expected 3.0 second break tags between sections.")

        if "<break time=\"1.5s\"" not in text and "<break time='1.5s'" not in text:
            warnings.append("Expected 1.5 second break tags after section titles.")

    if not warnings:
        if model_id == "eleven_v3":
            warnings.append(
                "Pause timing is approximate when using eleven_v3 structured text.",
            )
        else:
            warnings.append(
                "Break tag behavior must be validated on the selected ElevenLabs model and voice.",
            )

    return ValidationResult(
        valid=not errors,
        errors=errors,
        warnings=warnings,
    )
