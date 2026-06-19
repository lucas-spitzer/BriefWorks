from app.mathesys.audio.segment_text import sanitize_segment_text


def test_sanitize_segment_text_strips_sup_tags() -> None:
    cleaned = sanitize_segment_text(
        'Clausewitz wrote, the defense is "not a simple shield."<sup>13</sup>',
    )

    assert "<sup>" not in cleaned
    assert "13" not in cleaned
    assert cleaned.endswith('"not a simple shield."')
