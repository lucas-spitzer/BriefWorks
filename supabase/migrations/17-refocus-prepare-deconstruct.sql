-- Refocus prepare-document and deconstruct-document v2.0
-- Add document_chapters for persisted chapter/section segmentation

create table public.document_chapters (
  id uuid primary key default gen_random_uuid(),
  source_id uuid not null references public.sources (id) on delete cascade,
  workspace_id uuid not null references public.workspaces (id) on delete cascade,
  sequence_index integer not null,
  title text not null,
  level integer not null default 1,
  segment_ids uuid[] not null,
  created_at timestamptz not null default now(),
  constraint document_chapters_source_sequence_key
    unique (source_id, sequence_index)
);

create index document_chapters_source_id_idx on public.document_chapters (source_id);
create index document_chapters_workspace_id_idx on public.document_chapters (workspace_id);

alter table public.document_chapters enable row level security;

revoke all on table public.document_chapters from anon, authenticated;

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
  'prepare-document',
  '2.0',
  'intellex',
  'Prepare Document',
  'Remove all non-learning content; keep only chapter/section headings and their body text.',
  array['text'],
  '{"type":"object","properties":{"source_id":{"type":"string"},"line_count":{"type":"integer"},"page_count":{"type":"integer"}}}'::jsonb,
  '{"type":"object","properties":{"excluded_line_ids":{"type":"array"},"excluded_pages":{"type":"array"},"kept_line_count":{"type":"integer"},"excluded_line_count":{"type":"integer"},"pre_filter":{"type":"object"},"validation":{"type":"object"}}}'::jsonb,
  '{"system":"Extract learning content only: chapter/section headings and body text that teaches the subject. Remove TOC, glossaries, indexes, prefaces, page numbers, and all front/back matter.","user_template":"Prepare source {{source_id}} for learning content extraction."}'::jsonb
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
  'deconstruct-document',
  '2.0',
  'intellex',
  'Deconstruct Document',
  'Segment prepared document into chapters/sections for downstream chapter-by-chapter processing.',
  array['text'],
  '{"type":"object","properties":{"source_id":{"type":"string"},"segment_count":{"type":"integer"}}}'::jsonb,
  '{"type":"object","required":["chapters"],"properties":{"chapters":{"type":"array","items":{"type":"object","required":["sequence_index","title","level","segment_ids"],"properties":{"sequence_index":{"type":"integer"},"title":{"type":"string"},"level":{"type":"integer"},"segment_ids":{"type":"array"}}}}}}'::jsonb,
  '{"system":"Segment the document into chapters and sections. Assign every segment_id to exactly one chapter. Do not extract key terms.","user_template":"Segment source {{source_id}} into chapters from NDR segments."}'::jsonb
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
