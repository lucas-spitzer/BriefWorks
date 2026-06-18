-- Mathesys audio skills: seed the narration skills that were never seeded
-- (so skill_runs no longer violate the skill_runs_skill_fk foreign key),
-- rename ElevenReader to its EBook label, and retire Speechify EPUB.

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
values
  (
    'speechify-audio',
    '1.0.0',
    'mathesys',
    'Speechify Audio',
    'Convert source text to clean SSML, then synthesize MP3 audio through the Speechify API.',
    array['text', 'audio'],
    '{"type":"object","properties":{"source_id":{"type":"string"},"wiki_entry_ids":{"type":"array"}}}'::jsonb,
    '{"type":"object","properties":{"files":{"type":"array"},"manifest":{"type":"object"}}}'::jsonb,
    '{
      "system": "Transform source text into clean, listenable SSML, removing all non-content material, then synthesize audio with Speechify.",
      "user_template": "Generate Speechify audio for source {{source_id}}."
    }'::jsonb
  ),
  (
    'elevenlabs-audio',
    '1.0.0',
    'mathesys',
    'ElevenLabs Audio',
    'Convert source text to an ElevenLabs structured-text script, then synthesize MP3 audio through the ElevenLabs API.',
    array['text', 'audio'],
    '{"type":"object","properties":{"source_id":{"type":"string"},"wiki_entry_ids":{"type":"array"}}}'::jsonb,
    '{"type":"object","properties":{"files":{"type":"array"},"manifest":{"type":"object"}}}'::jsonb,
    '{
      "system": "Transform source text into clean ElevenLabs structured narration text, removing all non-content material, then synthesize audio with ElevenLabs.",
      "user_template": "Generate ElevenLabs audio for source {{source_id}}."
    }'::jsonb
  )
on conflict (skill_id, version) do nothing;

-- Speechify EPUB is retired in favor of Speechify Audio.
update public.skills
set is_active = false
where skill_id = 'speechify-app-epub';
