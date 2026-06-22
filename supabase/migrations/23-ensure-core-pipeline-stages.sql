-- Ensure Intellex stages required by the structure-based pipeline exist.
-- Migrations 21–22 only registered parse + structuring stages; databases that
-- skipped earlier migration history (or ran a partial setup) may be missing
-- source-research and extract-knowledge.

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
    'source-research',
    '1.0.0',
    'intellex',
    'Source Research',
    'Extract title, issuing authority, version, publication date, and distribution line from early parsed pages with optional web gap-fill for title and authority.',
    array['text'],
    '{"type":"object","properties":{"source_id":{"type":"string"},"parsed_text":{"type":"string"}}}'::jsonb,
    '{
      "type": "object",
      "required": ["document_type", "title"],
      "properties": {
        "document_type": {"type": "string"},
        "title": {"type": "string"},
        "identifier": {"type": "string"},
        "issuing_authority": {"type": "string"},
        "authors": {"type": "array"},
        "version": {"type": "string"},
        "publication_date_in_document": {"type": "string"},
        "publication_date_public": {"type": "string"},
        "source_url": {"type": "string"},
        "abstract": {"type": "string"},
        "distribution_line": {"type": "string"},
        "confidence": {"type": "object"},
        "provenance": {"type": "object"},
        "web_sources": {"type": "array"}
      }
    }'::jsonb,
    '{
      "system": "Extract bibliographic metadata from the early pages of a parsed document: title, issuing authority, version, publication date, and distribution line.",
      "user_template": "Metadata slice extraction for source {{source_id}}."
    }'::jsonb
  ),
  (
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
on conflict (stage_id, version) do update
set
  module = excluded.module,
  name = excluded.name,
  description = excluded.description,
  modalities = excluded.modalities,
  input_schema = excluded.input_schema,
  output_schema = excluded.output_schema,
  prompts = excluded.prompts;
