-- Markdown-faithful copy of segment text for the Reader.
--
-- ndr_segments.text stays PLAIN (flattened emphasis) because it feeds LLM
-- consumption, retrieval embeddings, and narration alignment. `md` carries the
-- original inline markdown (*em* / **strong**) so the Reader can render
-- emphasis without re-parsing the source. Populated by the chunk step going
-- forward; backfilled from the persisted structure/book.json artifact by
-- scripts/backfill_segment_md.py. Null when the markdown adds nothing over
-- the plain text (the common case), so storage cost stays negligible.

alter table public.ndr_segments
  add column if not exists md text;
