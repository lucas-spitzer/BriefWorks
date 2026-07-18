-- The generate-narration stage now also publishes a downloadable artifact:
-- a ZIP of the per-paragraph mp3 files plus a manifest.json with word-level
-- timings, mirroring how Create EBook publishes the epub. The per-segment
-- narration_segments rows remain the Reader's source of truth; the artifact
-- is the export/download surface.

alter table public.artifacts
  drop constraint if exists artifacts_type_check;

alter table public.artifacts
  add constraint artifacts_type_check
    check (
      artifact_type in (
        'electronic_book',
        'narration_audio',
        'wiki_json'
      )
    );
