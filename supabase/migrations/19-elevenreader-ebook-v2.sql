-- ElevenReader EBook v2: chapter-based single EPUB

insert into public.skills (
  skill_id,
  version,
  module,
  name,
  description,
  modalities,
  input_schema,
  output_schema,
  prompts
)
values (
  'elevenreader-ebook',
  '2.0',
  'mathesys',
  'ElevenReader EBook',
  'Build one simple, audio-friendly EPUB from document chapters (titles + subsection headings + body text) for manual ElevenReader upload.',
  array['text'],
  '{"type":"object","properties":{"source_id":{"type":"string"},"segment_count":{"type":"integer"},"chapter_count":{"type":"integer"}}}'::jsonb,
  '{"type":"object","properties":{"files":{"type":"array"},"chapter_count":{"type":"integer"},"chapter_titles":{"type":"array"}}}'::jsonb,
  '{"system":"Build one EPUB per source from persisted document_chapters. Each chapter becomes one spine item with an h1 title, h2 subsection headings, and paragraph body text. No LLM transformation.","user_template":"Generate ElevenReader EPUB for source {{source_id}} with {{chapter_count}} chapters."}'::jsonb
)
on conflict (skill_id, version) do update
set
  module = excluded.module,
  name = excluded.name,
  description = excluded.description,
  modalities = excluded.modalities,
  input_schema = excluded.input_schema,
  output_schema = excluded.output_schema,
  prompts = excluded.prompts;
