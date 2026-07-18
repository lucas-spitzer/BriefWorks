-- Remove the Speechify/ElevenLabs audio artifacts and rename the ElevenReader
-- EBook artifact to a clearer name. Narration audio synthesis (speechify_script,
-- speechify_audio, elevenlabs_audio) and its supporting stage code have been
-- deleted from the API; eleven_reader_script becomes electronic_book.
--
-- Stage rows for the removed artifacts are deactivated rather than deleted —
-- stage_runs.stage_id/stage_version has a FK into stages, so historical stage
-- runs must keep a resolvable row.

-- ---------------------------------------------------------------------------
-- 1. Drop the constraint first — the rename below writes a value
--    ('electronic_book') that the existing check does not yet permit.
-- ---------------------------------------------------------------------------

alter table public.artifacts
  drop constraint if exists artifacts_type_check;

-- ---------------------------------------------------------------------------
-- 2. Data: rename electronic_book, drop rows for removed artifact types.
-- ---------------------------------------------------------------------------

update public.artifacts
set artifact_type = 'electronic_book'
where artifact_type = 'eleven_reader_script';

delete from public.artifacts
where artifact_type in ('speechify_script', 'speechify_audio', 'elevenlabs_audio');

-- ---------------------------------------------------------------------------
-- 3. Tighten the artifacts type constraint to the surviving set.
-- ---------------------------------------------------------------------------

alter table public.artifacts
  add constraint artifacts_type_check
    check (
      artifact_type in (
        'electronic_book',
        'wiki_json'
      )
    );

-- ---------------------------------------------------------------------------
-- 4. Deactivate the removed stages; rename the trimmed stage's display name.
-- ---------------------------------------------------------------------------

update public.stages
set is_active = false
where stage_id in ('speechify-audio', 'elevenlabs-audio');

update public.stages
set name = 'Trim Document'
where stage_id = 'trim-document-boundaries';

-- ---------------------------------------------------------------------------
-- 5. Rewrite pending production runs referencing the removed/renamed keys.
-- ---------------------------------------------------------------------------

update public.production_runs
set target_artifacts = array_replace(
  target_artifacts,
  'eleven_reader_script',
  'electronic_book'
)
where 'eleven_reader_script' = any(target_artifacts);

update public.production_runs
set target_artifacts = coalesce(
  (
    select array_agg(value)
    from unnest(target_artifacts) as value
    where value not in ('speechify_script', 'speechify_audio', 'elevenlabs_audio')
  ),
  '{}'
)
where status = 'pending'
  and target_artifacts && array['speechify_script', 'speechify_audio', 'elevenlabs_audio']::text[];

update public.production_runs
set pipeline = (
  select coalesce(jsonb_agg(elem), '[]'::jsonb)
  from jsonb_array_elements(pipeline) as elem
  where elem->>'step' not in ('speechify-audio', 'elevenlabs-audio')
)
where status = 'pending'
  and (
    pipeline @> '[{"step": "speechify-audio"}]'::jsonb
    or pipeline @> '[{"step": "elevenlabs-audio"}]'::jsonb
  );
