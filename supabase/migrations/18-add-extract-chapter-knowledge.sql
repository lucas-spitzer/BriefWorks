-- Extract chapter knowledge skill + wiki entry_kind discriminator

alter table public.wiki_entries
  add column if not exists entry_kind text not null default 'concept';

alter table public.wiki_entries
  drop constraint if exists wiki_entries_entry_kind_check;

alter table public.wiki_entries
  add constraint wiki_entries_entry_kind_check
  check (entry_kind in ('term', 'concept', 'insight'));

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
  'extract-knowledge',
  '1.0.0',
  'intellex',
  'Extract Knowledge',
  'Extract terms, concepts, and insights from each chapter via isolated LLM calls.',
  array['text'],
  '{"type":"object","properties":{"source_id":{"type":"string"},"chapter_count":{"type":"integer"},"segment_count":{"type":"integer"}}}'::jsonb,
  '{"type":"object","properties":{"chapters":{"type":"array"},"items":{"type":"array"},"item_counts":{"type":"object"}}}'::jsonb,
  '{"system":"Extract terms, concepts, and insights from one chapter at a time. Ground every item in chapter segment text.","user_template":"Extract knowledge for chapter {{chapter_title}} in source {{source_id}}."}'::jsonb
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
