from app.intellex.content_filter import filter_segments_for_audio


def _seg(seg_id: str, kind: str, text: str, page: int = 1) -> dict:
    return {"id": seg_id, "kind": kind, "text": text, "locator": {"page": page}}


def test_drops_front_and_back_matter_chapters() -> None:
    segments = [
        _seg("h-toc", "heading", "Table of Contents", page=1),
        _seg("toc-1", "paragraph", "Introduction 1", page=1),
        _seg("h-ch1", "heading", "Chapter 1: Operations", page=2),
        _seg("ch1-1", "paragraph", "Operations require clear intent.", page=2),
        _seg("h-index", "heading", "Index", page=99),
        _seg("idx-1", "paragraph", "operations, 2", page=99),
    ]

    kept, report = filter_segments_for_audio(segments)
    kept_ids = [segment["id"] for segment in kept]

    assert kept_ids == ["h-ch1", "ch1-1"]
    assert "Table of Contents" in report["dropped_chapters"]
    assert "Index" in report["dropped_chapters"]


def test_drops_clutter_segments() -> None:
    segments = [
        _seg("h", "heading", "Chapter 1", page=1),
        _seg("body", "paragraph", "This is the real body content of the chapter.", page=1),
        _seg("pageno", "paragraph", "12", page=1),
        _seg("dots", "paragraph", "Introduction ............ 4", page=1),
        _seg("caption", "paragraph", "Figure 3. The command structure diagram.", page=2),
        _seg("marker", "paragraph", "[12]", page=2),
        _seg("blank", "paragraph", "This page intentionally left blank.", page=3),
        _seg("url", "paragraph", "https://example.com/doc", page=3),
    ]

    kept, report = filter_segments_for_audio(segments)
    kept_ids = [segment["id"] for segment in kept]

    assert kept_ids == ["h", "body"]
    assert report["reasons"]["page_number"] == 1
    assert report["reasons"]["toc_dot_leader"] == 1
    assert report["reasons"]["figure_table_caption"] == 1
    assert report["reasons"]["citation_marker"] == 1
    assert report["reasons"]["blank_page_notice"] == 1
    assert report["reasons"]["bare_url_or_doi"] == 1


def test_drops_repeated_running_headers() -> None:
    segments = [_seg("h", "heading", "Chapter 1", page=1)]
    for page in range(1, 6):
        segments.append(
            _seg(f"hdr-{page}", "paragraph", "Field Manual 3-0", page=page),
        )
    segments.append(_seg("body", "paragraph", "Real narratable content here.", page=1))

    kept, report = filter_segments_for_audio(segments)
    kept_ids = [segment["id"] for segment in kept]

    assert "body" in kept_ids
    assert not any(seg_id.startswith("hdr-") for seg_id in kept_ids)
    assert report["reasons"]["running_header_footer"] == 5


def test_drops_glossary_and_list_of_tables_headings() -> None:
    segments = [
        _seg("h-gloss", "heading", "Glossary of Terms", page=80),
        _seg("gloss-1", "paragraph", "Maneuver warfare: a way of thinking.", page=80),
        _seg("h-body", "heading", "Chapter 2", page=10),
        _seg("body-1", "paragraph", "Operations require clear intent.", page=10),
        _seg("h-lot", "heading", "List of Tables", page=2),
        _seg("lot-1", "paragraph", "Table 3-1 Command structure", page=2),
    ]

    kept, report = filter_segments_for_audio(segments)
    kept_ids = [segment["id"] for segment in kept]

    assert kept_ids == ["h-body", "body-1"]
    assert "Glossary of Terms" in report["dropped_chapters"]
    assert "List of Tables" in report["dropped_chapters"]


def test_keeps_body_only_document_unchanged() -> None:
    segments = [
        _seg("h", "heading", "Chapter 1: Doctrine", page=1),
        _seg("p1", "paragraph", "Doctrine guides decisions under uncertainty.", page=1),
        _seg("p2", "paragraph", "Commanders apply judgment to the situation.", page=2),
    ]

    kept, report = filter_segments_for_audio(segments)

    assert [segment["id"] for segment in kept] == ["h", "p1", "p2"]
    assert report["dropped_segment_count"] == 0
