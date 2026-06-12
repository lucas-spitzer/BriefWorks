from app.mathesys.audio.emitters.eleven_labs_structured_text import emit_eleven_labs_structured_text
from app.mathesys.audio.emitters.speechify_ssml import emit_speechify_ssml
from app.mathesys.audio.models import (
    AudioDocument,
    AudioParagraph,
    AudioSection,
)
from app.mathesys.audio.validation.validate_eleven_labs_text import validate_eleven_labs_text
from app.mathesys.audio.validation.validate_ssml import validate_ssml


def _sample_document() -> AudioDocument:
    return AudioDocument(
        title="Mission Brief",
        language="en-US",
        sections=[
            AudioSection(
                id="s1",
                level=1,
                title="Mission Brief",
                paragraphs=[
                    AudioParagraph(
                        id="p1",
                        text="The landing zone is narrow. Use infrared strobes after touchdown.",
                    ),
                ],
            ),
            AudioSection(
                id="s2",
                level=1,
                title="Extraction",
                paragraphs=[
                    AudioParagraph(
                        id="p2",
                        text="Check fuel, confirm E T A, then move west.",
                    ),
                ],
            ),
        ],
    )


def test_emit_speechify_ssml_includes_required_pause_tags() -> None:
    output = emit_speechify_ssml(_sample_document())
    validation = validate_ssml(output)

    assert validation.valid
    assert '<break time="1.5s"/>' in output.ssml
    assert '<break time="3.0s"/>' in output.ssml
    assert output.ssml.startswith("<speak>")
    assert output.ssml.endswith("</speak>")


def test_emit_eleven_labs_expressive_avoids_ssml_breaks() -> None:
    output = emit_eleven_labs_structured_text(_sample_document(), mode="expressive_v3")
    validation = validate_eleven_labs_text(output)

    assert validation.valid
    assert "[long pause]" in output.text
    assert "[short pause]" in output.text
    assert "<break" not in output.text
    assert output.model_id == "eleven_v3"


def test_emit_eleven_labs_strict_uses_break_tags() -> None:
    output = emit_eleven_labs_structured_text(
        _sample_document(),
        mode="strict_pause_fallback",
    )
    validation = validate_eleven_labs_text(output)

    assert validation.valid
    assert '<break time="3.0s" />' in output.text
    assert '<break time="1.5s" />' in output.text
    assert "[long pause]" not in output.text
