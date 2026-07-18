-- Synthesized narration for the Reader (generate-narration stage).
--
-- One row per narrated paragraph segment: the audio file lives in the sources
-- bucket next to the source's structure artifacts, and `words` carries the
-- word-level timings derived from ElevenLabs' character alignment
-- ([{i, w, s, e}] — word index, word, start/end seconds). Keyed by
-- (segment_id, voice_id) so re-runs are idempotent and a future voice picker
-- can narrate the same text twice. Cascades with ndr_segments: re-chunking a
-- source deletes its segments and therefore its stale narration.

create table public.narration_segments (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces (id) on delete cascade,
  source_id uuid not null references public.sources (id) on delete cascade,
  chapter_id uuid references public.document_chapters (id) on delete set null,
  segment_id uuid not null references public.ndr_segments (id) on delete cascade,
  voice_id text not null,
  model_id text not null,
  audio_path text not null,
  duration_seconds double precision not null default 0,
  words jsonb not null default '[]',
  request_id text,
  character_count integer not null default 0,
  created_at timestamptz not null default now(),
  constraint narration_segments_segment_voice_key
    unique (segment_id, voice_id)
);

create index narration_segments_source_id_idx
on public.narration_segments (source_id);

create index narration_segments_workspace_id_idx
on public.narration_segments (workspace_id);

alter table public.narration_segments enable row level security;

revoke all on table public.narration_segments from anon, authenticated;

-- Register the stage so stage_runs can reference it.

insert into public.stages (
  stage_id,
  version,
  module,
  name,
  description,
  modalities,
  input_schema,
  output_schema,
  prompts
)
values
  (
    'generate-narration',
    '1.0',
    'mathesys',
    'Generate Narration',
    'Synthesize per-paragraph ElevenLabs narration with character-level timing, stored as narration_segments rows for the Reader''s read-while-listen mode.',
    array['text', 'audio'],
    '{"type":"object","properties":{"source_id":{"type":"string"},"voice_id":{"type":"string"},"model_id":{"type":"string"}}}'::jsonb,
    '{"type":"object","properties":{"segments_narrated":{"type":"integer"},"segments_reused":{"type":"integer"},"segments_skipped":{"type":"integer"},"character_count":{"type":"integer"}}}'::jsonb,
    '{}'::jsonb
  )
on conflict (stage_id, version) do update
set
  module = excluded.module,
  name = excluded.name,
  description = excluded.description,
  modalities = excluded.modalities,
  input_schema = excluded.input_schema,
  output_schema = excluded.output_schema,
  prompts = excluded.prompts,
  is_active = true;
