"""Sanitize model HTML and wrap it in owned print chrome."""

from __future__ import annotations

from html import escape
from html.parser import HTMLParser

SKIP_TAGS = frozenset({"script", "style", "iframe", "object", "embed", "link", "meta"})
VOID_TAGS = frozenset({"br", "hr"})
ALLOWED_TAGS = frozenset(
    {
        "section",
        "div",
        "span",
        "p",
        "h1",
        "h2",
        "h3",
        "h4",
        "ul",
        "ol",
        "li",
        "dl",
        "dt",
        "dd",
        "table",
        "thead",
        "tbody",
        "tr",
        "th",
        "td",
        "strong",
        "em",
        "b",
        "i",
        "code",
        "small",
        "blockquote",
        "br",
        "hr",
        "sup",
        "sub",
        "svg",
        "g",
        "path",
        "line",
        "circle",
        "rect",
        "polyline",
        "polygon",
        "text",
        "tspan",
        "title",
    }
)
ALLOWED_CLASSES = frozenset(
    {
        "section",
        "cols-2",
        "list-compact",
        "formula",
        "callout",
        "kicker",
        "lead",
    }
)
_GLOBAL_ATTRS = frozenset({"class"})
_TABLE_ATTRS = frozenset({"class", "colspan", "rowspan"})
_SVG_ATTRS = frozenset(
    {
        "class",
        "viewbox",
        "width",
        "height",
        "xmlns",
        "d",
        "fill",
        "stroke",
        "stroke-width",
        "stroke-linecap",
        "stroke-linejoin",
        "transform",
        "x",
        "y",
        "x1",
        "y1",
        "x2",
        "y2",
        "cx",
        "cy",
        "r",
        "rx",
        "ry",
        "points",
        "text-anchor",
        "font-size",
        "font-family",
    }
)
_ATTRS_BY_TAG = {
    "td": _TABLE_ATTRS,
    "th": _TABLE_ATTRS,
    "svg": _SVG_ATTRS,
    "g": _SVG_ATTRS,
    "path": _SVG_ATTRS,
    "line": _SVG_ATTRS,
    "circle": _SVG_ATTRS,
    "rect": _SVG_ATTRS,
    "polyline": _SVG_ATTRS,
    "polygon": _SVG_ATTRS,
    "text": _SVG_ATTRS,
    "tspan": _SVG_ATTRS,
}

PRINT_CSS = """
@page {
  size: letter;
  margin: 0.55in 0.5in 0.65in 0.5in;
  @bottom-center {
    content: counter(page) " / " counter(pages);
    font-size: 8pt;
    color: #818283;
    font-family: Arial, Helvetica, sans-serif;
  }
}
html, body {
  margin: 0;
  padding: 0;
  color: #000;
  background: #fff;
  font-family: Arial, Helvetica, sans-serif;
  font-size: 10pt;
  line-height: 1.28;
}
.sheet-chrome {
  margin: 0 0 10pt 0;
  padding: 0 0 6pt 0;
  border-bottom: 2pt solid #84754E;
}
.sheet-kicker {
  margin: 0 0 2pt 0;
  font-size: 8pt;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #84754E;
}
.sheet-title {
  margin: 0;
  font-size: 16pt;
  line-height: 1.15;
  color: #940000;
  font-weight: 700;
}
.sheet-body h1, .sheet-body h2, .sheet-body h3, .sheet-body h4 {
  color: #940000;
  font-weight: 700;
  page-break-after: avoid;
}
.sheet-body h2 { font-size: 11pt; margin: 9pt 0 3pt 0; }
.sheet-body h3 { font-size: 10pt; margin: 8pt 0 2pt 0; }
.sheet-body h4 { font-size: 10pt; margin: 6pt 0 2pt 0; }
.sheet-body p, .sheet-body li, .sheet-body dd { margin: 0 0 3pt 0; }
.sheet-body ul, .sheet-body ol { margin: 0 0 6pt 1.1em; padding: 0; }
.sheet-body .list-compact li { margin: 0 0 1pt 0; }
.sheet-body table {
  width: 100%;
  border-collapse: collapse;
  margin: 0 0 8pt 0;
  font-size: 9pt;
}
.sheet-body th, .sheet-body td {
  border: 0.5pt solid #D8D8D6;
  padding: 2pt 4pt;
  text-align: left;
  vertical-align: top;
}
.sheet-body th { background: #F7F7F5; }
.sheet-body .cols-2 {
  columns: 2;
  column-gap: 14pt;
}
.sheet-body .callout {
  border-left: 3pt solid #84754E;
  padding: 2pt 0 2pt 6pt;
  margin: 0 0 6pt 0;
}
.sheet-body .formula { font-family: "Courier New", Courier, monospace; }
.sheet-body svg { max-width: 100%; height: auto; display: block; margin: 4pt 0; }
.sheet-body hr { border: 0; border-top: 0.75pt solid #84754E; margin: 8pt 0; }
"""


class _BodySanitizer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.lower()
        if self._skip_depth:
            if lowered in SKIP_TAGS:
                self._skip_depth += 1
            return
        if lowered in SKIP_TAGS:
            self._skip_depth = 1
            return
        if lowered not in ALLOWED_TAGS:
            return
        rendered = _render_start(lowered, attrs)
        if rendered:
            self.parts.append(rendered)

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if self._skip_depth:
            if lowered in SKIP_TAGS:
                self._skip_depth -= 1
            return
        if lowered in SKIP_TAGS or lowered not in ALLOWED_TAGS or lowered in VOID_TAGS:
            return
        self.parts.append(f"</{lowered}>")

    def handle_data(self, data: str) -> None:
        if self._skip_depth or not data:
            return
        self.parts.append(escape(data, quote=False))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.lower()
        if self._skip_depth or lowered in SKIP_TAGS or lowered not in ALLOWED_TAGS:
            return
        rendered = _render_start(lowered, attrs, self_closing=True)
        if rendered:
            self.parts.append(rendered)


def _render_start(
    tag: str,
    attrs: list[tuple[str, str | None]],
    *,
    self_closing: bool = False,
) -> str | None:
    allowed = _ATTRS_BY_TAG.get(tag, _GLOBAL_ATTRS)
    cleaned: list[str] = []
    for raw_name, raw_value in attrs:
        name = (raw_name or "").lower()
        if name not in allowed or name.startswith("on"):
            continue
        value = raw_value or ""
        if name == "class":
            kept = [cls for cls in value.split() if cls in ALLOWED_CLASSES]
            if not kept:
                continue
            value = " ".join(kept)
        cleaned.append(f'{name}="{escape(value, quote=True)}"')
    attr_html = (" " + " ".join(cleaned)) if cleaned else ""
    if tag in VOID_TAGS or self_closing:
        return f"<{tag}{attr_html} />"
    return f"<{tag}{attr_html}>"


def sanitize_body_html(raw: str) -> str:
    parser = _BodySanitizer()
    parser.feed(raw or "")
    parser.close()
    return "".join(parser.parts).strip()


def wrap_sheet_html(*, title: str, body_html: str) -> str:
    safe_title = escape(title.strip() or "Study sheet")
    return (
        "<!DOCTYPE html><html><head><meta charset=\"utf-8\" />"
        f"<title>{safe_title}</title><style>{PRINT_CSS}</style></head><body>"
        "<header class=\"sheet-chrome\">"
        "<p class=\"sheet-kicker\">Arsenal study sheet</p>"
        f"<h1 class=\"sheet-title\">{safe_title}</h1>"
        "</header>"
        f"<main class=\"sheet-body\">{body_html}</main>"
        "</body></html>"
    )
