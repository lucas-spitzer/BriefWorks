from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

AudioOutputTarget = Literal[
    "elevenreader_app_epub",
    "speechify_api_ssml",
    "elevenlabs_api_structured_text",
]

ParagraphType = Literal[
    "normal",
    "quote",
    "list_item",
    "table_summary",
    "image_description",
    "note",
]

ElevenLabsMode = Literal["expressive_v3", "strict_pause_fallback"]


class AudioParagraph(BaseModel):
    id: str
    text: str
    type: ParagraphType = "normal"


class AudioSection(BaseModel):
    id: str
    level: Literal[1, 2, 3, 4]
    title: str
    paragraphs: list[AudioParagraph] = Field(default_factory=list)
    subsections: list[AudioSection] = Field(default_factory=list)


class PronunciationEntry(BaseModel):
    term: str
    replacement: str | None = None
    ipa: str | None = None
    alias: str | None = None
    notes: str | None = None


class AudioDocument(BaseModel):
    title: str
    subtitle: str | None = None
    author: str | None = None
    language: str = "en-US"
    source_type: Literal["pdf", "docx", "markdown", "txt"] = "pdf"
    audience: str | None = None
    sections: list[AudioSection] = Field(default_factory=list)
    glossary: list[PronunciationEntry] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)


class EpubChapterOutput(BaseModel):
    id: str
    title: str
    level: int
    filename: str
    xhtml: str
    chapter_start: bool = False


class SpeechifySsmlOutput(BaseModel):
    ssml: str
    section_count: int
    estimated_character_count: int
    warnings: list[str] = Field(default_factory=list)


class ElevenLabsVoiceSettings(BaseModel):
    stability: float | None = None
    similarity_boost: float = 0.75
    style: float = 0.0
    speed: float = 1.0


class ElevenLabsPronunciationLocator(BaseModel):
    pronunciation_dictionary_id: str
    version_id: str


class ElevenLabsStructuredTextOutput(BaseModel):
    text: str
    model_id: str
    language_code: str = "en"
    voice_settings: ElevenLabsVoiceSettings | None = None
    pronunciation_dictionary_locators: list[ElevenLabsPronunciationLocator] = Field(
        default_factory=list,
    )
    previous_text: str | None = None
    next_text: str | None = None
    seed: int | None = None
    warnings: list[str] = Field(default_factory=list)


class ValidationResult(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ChapterBuildResult(BaseModel):
    section: AudioSection
    segment_ids_used: list[str] = Field(default_factory=list)
    wiki_ids_cited: list[str] = Field(default_factory=list)
