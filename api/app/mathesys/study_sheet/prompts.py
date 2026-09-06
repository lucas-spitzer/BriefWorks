"""Prompts for study-sheet HTML generation.

The prompt describes allowed *blocks*, not a layout borrowed from any one
source shape (numbered lists, markdown headings, acronyms).
"""

from __future__ import annotations

PRINT_GEOMETRY = """Print geometry (fixed; do not override in HTML):
- US Letter, duplex on the long edge
- Margins 0.55in top, 0.5in sides, 0.65in bottom
- Body 10pt Arial, black
- Section headings 11pt scarlet
- Header chrome uses about 0.6in
- Density classes you may use: section, cols-2, list-compact, formula, callout
- Do not set font-size, color, or page CSS. Do not emit <html>, <head>, <style>, or <script>.
"""

SYSTEM_PROMPT = f"""You compress source material into a printable study sheet.

The sheet is a memory map: what is worth retrieving, packed onto at most two letter pages. It is not a rewrite, a lesson, or a worksheet.

{PRINT_GEOMETRY}

Rules:
1. Extract and compress only. Reorder and group if that helps scanning. Do not add facts, mnemonics, examples, or diagrams that are not in the source.
2. The whole file is the subject. Cover the material that a learner would memorize from this file. Drop padding, repetition, and long worked prose.
3. If the source already looks like a sheet (short lists, definitions, procedures), keep that structure. If it is prose, tables, or mixed, compress to the same block types. Do not force numbered lists onto prose that is not a sequence.
4. Recreate a source diagram or formula only as simple inline SVG or text, and only when the source already has it. No decorative graphics.
5. Use these HTML blocks as needed: section, h2/h3, p, ul/ol/li, dl/dt/dd, table, strong, code, span.formula, div.callout, svg. Class names: section, cols-2, list-compact, formula, callout.

Return a JSON object:
{{
  "title": string,
  "body_html": string
}}

body_html is a fragment for the sheet body. No full document. No markdown fences.
"""


def user_prompt_for_markdown(*, filename: str, text: str, retry_note: str | None) -> str:
    retry = f"\n\n{retry_note}" if retry_note else ""
    return (
        f"Source filename: {filename}\n"
        "Source format: markdown text.\n\n"
        f"{text}{retry}"
    )


def user_prompt_for_pdf(*, filename: str, retry_note: str | None) -> str:
    retry = f"\n\n{retry_note}" if retry_note else ""
    return (
        f"Source filename: {filename}\n"
        "Source format: PDF document (attached).\n"
        "Read the attached PDF and produce the study sheet JSON."
        f"{retry}"
    )


def retry_note(*, page_count: int, max_pages: int) -> str:
    return (
        f"The previous HTML printed at {page_count} pages. "
        f"The budget is {max_pages} pages at the type scale above. "
        "Drop the lowest-priority material. Do not add facts. "
        "Do not shrink type or change colors."
    )
