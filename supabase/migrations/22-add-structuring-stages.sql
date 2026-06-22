-- Structure-based pipeline: add structuring stages, deactivate replaced stages,
-- and upgrade pending production_run pipeline definitions.

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
    'normalize-document',
    '1.0.0',
    'intellex',
    'Normalize Document',
    'Flatten LlamaParse structured pages into reading-order elements, dropping page furniture.',
    array['text'],
    '{"type":"object","properties":{"source_id":{"type":"string"},"page_count":{"type":"integer"}}}'::jsonb,
    '{"type":"object","properties":{"element_count":{"type":"integer"},"dropped_furniture":{"type":"object"}}}'::jsonb,
    '{"system":"Normalize LlamaParse structured layout into a flat element stream.","user_template":"Normalize source {{source_id}}."}'::jsonb
  ),
  (
    'trim-document-boundaries',
    '1.0.0',
    'intellex',
    'Trim Document Boundaries',
    'Detect and trim front/back matter before the first chapter and after back-matter markers.',
    array['text'],
    '{"type":"object","properties":{"source_id":{"type":"string"},"element_count":{"type":"integer"}}}'::jsonb,
    '{"type":"object","properties":{"start_index":{"type":"integer"},"end_index":{"type":"integer"},"kept_element_count":{"type":"integer"},"boundary_reasons":{"type":"object"}}}'::jsonb,
    '{"system":"Trim non-body front and back matter from normalized elements.","user_template":"Trim boundaries for source {{source_id}}."}'::jsonb
  ),
  (
    'structure-document',
    '1.0.0',
    'intellex',
    'Structure Document',
    'Classify trimmed elements into chapters, sections, and body paragraphs.',
    array['text'],
    '{"type":"object","properties":{"source_id":{"type":"string"},"element_count":{"type":"integer"}}}'::jsonb,
    '{"type":"object","properties":{"chapter_count":{"type":"integer"},"section_count":{"type":"integer"},"chapter_titles":{"type":"array"},"dropped_nontext":{"type":"object"}}}'::jsonb,
    '{"system":"Build a chapter/section Book model from trimmed elements.","user_template":"Structure source {{source_id}}."}'::jsonb
  ),
  (
    'validate-structure',
    '1.0.0',
    'intellex',
    'Validate Structure',
    'Cross-check the structured Book against the source PDF; raises on hard failure.',
    array['text'],
    '{"type":"object","properties":{"source_id":{"type":"string"},"chapter_count":{"type":"integer"}}}'::jsonb,
    '{"type":"object","properties":{"valid":{"type":"boolean"},"warnings":{"type":"array"},"checked":{"type":"object"}}}'::jsonb,
    '{"system":"Validate structured book against source PDF text layer.","user_template":"Validate structure for source {{source_id}}."}'::jsonb
  ),
  (
    'create-ebook',
    '1.0.0',
    'mathesys',
    'Create EBook',
    'Render the structured Book to an EPUB for manual ElevenReader upload.',
    array['text'],
    '{"type":"object","properties":{"source_id":{"type":"string"},"chapter_count":{"type":"integer"}}}'::jsonb,
    '{"type":"object","properties":{"files":{"type":"array"},"chapter_titles":{"type":"array"}}}'::jsonb,
    '{"system":"Build one EPUB per source from the persisted structured Book.","user_template":"Create EPUB for source {{source_id}} with {{chapter_count}} chapters."}'::jsonb
  )
on conflict (stage_id, version) do update
set
  module = excluded.module,
  name = excluded.name,
  description = excluded.description,
  modalities = excluded.modalities,
  input_schema = excluded.input_schema,
  output_schema = excluded.output_schema,
  prompts = excluded.prompts;

update public.stages
set is_active = false
where stage_id in ('prepare-document', 'deconstruct-document', 'elevenreader-ebook');

-- Rewrite pending production runs that still reference the old pipeline steps.
update public.production_runs
set pipeline = (
  select coalesce(jsonb_agg(
    case elem->>'step'
      when 'prepare-document' then
        jsonb_build_object(
          'step', 'normalize-document',
          'type', 'stage',
          'module', 'intellex',
          'stage_id', 'normalize-document',
          'stage_version', '1.0.0',
          'status', 'pending'
        )
      when 'deconstruct-document' then
        jsonb_build_object(
          'step', 'validate-structure',
          'type', 'stage',
          'module', 'intellex',
          'stage_id', 'validate-structure',
          'stage_version', '1.0.0',
          'status', 'pending'
        )
      when 'elevenreader-ebook' then
        jsonb_build_object(
          'step', 'create-ebook',
          'type', 'stage',
          'module', 'mathesys',
          'stage_id', 'create-ebook',
          'stage_version', '1.0.0',
          'status', 'pending'
        )
      else elem
    end
  ), '[]'::jsonb)
  from jsonb_array_elements(pipeline) as elem
)
where status = 'pending'
  and (
    pipeline @> '[{"step": "prepare-document"}]'::jsonb
    or pipeline @> '[{"step": "deconstruct-document"}]'::jsonb
    or pipeline @> '[{"step": "elevenreader-ebook"}]'::jsonb
  );
