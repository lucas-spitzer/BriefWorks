-- Expand artifact types for Document Narration outputs.

alter table public.artifacts
  drop constraint if exists artifacts_type_check;

alter table public.artifacts
  add constraint artifacts_type_check
    check (
      artifact_type in (
        'eleven_reader_script',
        'speechify_script',
        'speechify_audio',
        'elevenlabs_audio'
      )
    );
