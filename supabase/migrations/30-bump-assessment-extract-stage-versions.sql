-- Sync the stages registry with the code STAGE_VERSION after the QnGen and
-- extraction redesigns. The pipeline writes stage_runs.stage_version from the
-- executors (now 2.1); this updates the registry rows that the /stages API
-- surfaces so they no longer read 2.0. Nothing joins stage_runs to stages by
-- version, so an in-place bump is safe.
update public.stages
set version = '2.1'
where stage_id in (
    'generate-flashcards',
    'generate-questions',
    'generate-scenarios',
    'extract-knowledge'
)
  and version = '2.0';
