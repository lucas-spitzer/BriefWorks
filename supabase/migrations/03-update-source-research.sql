-- Refresh Source Research skill prompts to match implementation

update public.skills
set
  description = 'Extract and corroborate document metadata from parsed text with optional web gap-fill.',
  output_schema = '{
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
      "confidence": {"type": "object"},
      "provenance": {"type": "object"},
      "web_sources": {"type": "array"}
    }
  }'::jsonb,
  prompts = '{
    "system": "Extract bibliographic metadata from parsed document text first. Use web corroboration only for missing or low-confidence fields.",
    "user_template": "Research source {{source_id}} from parsed document text."
  }'::jsonb
where skill_id = 'source-research'
  and version = '1.0';
