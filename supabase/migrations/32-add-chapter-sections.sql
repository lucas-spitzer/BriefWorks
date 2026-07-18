-- Persist section structure (level-2 headings) on document_chapters.
--
-- The Reader flows the full segment stream and styles by heading level; the
-- pipeline only ever produces two levels (Chapter -> Section), so each section
-- here is one level-2 heading plus its body segments. Stored authoritatively
-- (rather than derived) so the chapters API and the artifact manifest stay
-- consistent. Shape per element:
--   { title, level, sequence_index, heading_segment_id, segment_ids[] }

alter table public.document_chapters
  add column if not exists sections jsonb not null default '[]';
