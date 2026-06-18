from app.mathesys.audio.audio_document_builder import AudioDocumentBuilder
from app.mathesys.audio.emitters.eleven_labs_structured_text import emit_eleven_labs_structured_text
from app.mathesys.audio.emitters.epub_emitter import audio_document_to_epub_chapters
from app.mathesys.audio.emitters.speechify_ssml import emit_speechify_ssml
from app.mathesys.audio.segment_to_document import chapter_to_audio_section


def test_chapter_to_audio_section_preserves_heading_and_body_text() -> None:
    chapter = {
        "title": "Chapter 1: Operations",
        "segments": [
            {
                "id": "h1",
                "kind": "heading",
                "text": "Chapter 1: Operations",
            },
            {
                "id": "p1",
                "kind": "paragraph",
                "text": "Operations require clear intent.",
            },
            {
                "id": "h2",
                "kind": "heading",
                "text": "1.1 Purpose",
            },
            {
                "id": "p2",
                "kind": "paragraph",
                "text": "Doctrine explains intent.",
            },
        ],
    }

    result = chapter_to_audio_section(chapter)

    assert result.section.title == "Chapter 1: Operations"
    assert [paragraph.text for paragraph in result.section.paragraphs] == [
        "Operations require clear intent.",
    ]
    assert len(result.section.subsections) == 1
    assert result.section.subsections[0].title == "1.1 Purpose"
    assert result.section.subsections[0].paragraphs[0].text == "Doctrine explains intent."


def test_audio_document_builder_passes_through_prepared_segments() -> None:
    chapters = [
        {
            "title": "Chapter 1",
            "segments": [
                {"id": "h1", "kind": "heading", "text": "Chapter 1"},
                {"id": "p1", "kind": "paragraph", "text": "Body text stays exact."},
            ],
        },
    ]

    document, execution = AudioDocumentBuilder().build_document(
        title="Test Doc",
        author="Author",
        source_metadata={"mime_type": "application/pdf", "filename": "doc.pdf"},
        chapters=chapters,
        wiki_entries=[],
    )

    assert execution["model"] == "deterministic-passthrough"
    assert execution["token_usage"] == {}
    assert document.sections[0].title == "Chapter 1"
    assert document.sections[0].paragraphs[0].text == "Body text stays exact."


def test_emitters_preserve_section_and_paragraph_text() -> None:
    chapter = {
        "title": "Mission Brief",
        "segments": [
            {"id": "h1", "kind": "heading", "text": "Mission Brief"},
            {"id": "p1", "kind": "paragraph", "text": "Use infrared strobes after touchdown."},
        ],
    }
    section = chapter_to_audio_section(chapter).section
    document, _ = AudioDocumentBuilder().build_document(
        title="Mission Brief",
        author="Author",
        source_metadata={"mime_type": "application/pdf", "filename": "doc.pdf"},
        chapters=[{"title": section.title, "segments": chapter["segments"]}],
        wiki_entries=[],
    )

    ssml = emit_speechify_ssml(document).ssml
    eleven = emit_eleven_labs_structured_text(document, mode="expressive_v3").text
    epub = audio_document_to_epub_chapters(document, target="elevenreader_app_epub")[0].xhtml

    assert "Mission Brief" in ssml
    assert "Use infrared strobes after touchdown." in ssml
    assert "Mission Brief" in eleven
    assert "Use infrared strobes after touchdown." in eleven
    assert "[focused] Mission Brief" not in eleven
    assert "<h1>Mission Brief</h1>" in epub
    assert "<p>Use infrared strobes after touchdown.</p>" in epub
