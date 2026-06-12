from __future__ import annotations

import html
from typing import Any

from ebooklib import epub


def _escape(text: str) -> str:
    return html.escape(text, quote=True)


def build_epub(
    *,
    title: str,
    author: str,
    identifier: str | None,
    language: str,
    publication_date: str | None,
    chapters: list[dict[str, Any]],
) -> bytes:
    book = epub.EpubBook()
    book.set_identifier(identifier or title)
    book.set_title(title)
    book.set_language(language)
    book.add_author(author)

    if publication_date:
        book.add_metadata("DC", "date", publication_date)

    epub_chapters: list[epub.EpubHtml] = []

    for index, chapter in enumerate(chapters, start=1):
        chapter_title = str(chapter.get("title") or f"Chapter {index}")
        file_name = f"chapter-{index:03d}.xhtml"
        epub_chapter = epub.EpubHtml(
            title=chapter_title,
            file_name=file_name,
            lang=language,
        )

        xhtml_body = chapter.get("xhtml_body")

        if xhtml_body:
            body_parts: list[str] = [str(xhtml_body)]
        else:
            body_parts = [f"<h1>{_escape(chapter_title)}</h1>"]

        if not xhtml_body:
            for section in chapter.get("sections", []):
                heading = section.get("heading")
                heading_level = int(section.get("heading_level") or 2)
                heading_level = min(max(heading_level, 2), 3)

                if heading:
                    body_parts.append(
                        f"<h{heading_level}>{_escape(str(heading))}</h{heading_level}>",
                    )

                for paragraph in section.get("paragraphs", []):
                    cleaned = str(paragraph).strip()

                    if cleaned:
                        body_parts.append(f"<p>{_escape(cleaned)}</p>")

        epub_chapter.content = (
            "<html xmlns='http://www.w3.org/1999/xhtml' lang='"
            f"{_escape(language)}'>"
            "<head><meta charset='utf-8'/><title>"
            f"{_escape(chapter_title)}</title></head><body>"
            f"{''.join(body_parts)}</body></html>"
        )
        book.add_item(epub_chapter)
        epub_chapters.append(epub_chapter)

    book.toc = epub_chapters
    book.spine = ["nav", *epub_chapters]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    from io import BytesIO

    buffer = BytesIO()
    epub.write_epub(buffer, book, {})
    return buffer.getvalue()
