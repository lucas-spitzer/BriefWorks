from __future__ import annotations

from typing import Any

DEFAULT_AUDIO_FORMAT_OPTIONS: dict[str, Any] = {
    "language": "en-US",
    "speechify": {
        "model": "simba-english",
        "audio_format": "mp3",
        "section_pause_seconds": 3.0,
        "title_pause_seconds": 1.5,
    },
    "eleven_labs": {
        "expressive_model": "eleven_v3",
        "strict_fallback_model": "eleven_multilingual_v2",
        "language_code": "en",
        "voice_settings": {
            "similarity_boost": 0.75,
            "style": 0.0,
            "speed": 1.0,
        },
        "section_pause_tag": "[long pause]",
        "title_pause_tag": "[short pause]",
    },
    "epub": {
        "version": "epub3",
        "toc_depth": 2,
        "split_level": 1,
        "use_fixed_layout": False,
    },
}

SPEECHIFY_SSML_CHARACTER_LIMIT = 500_000
