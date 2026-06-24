-- Refresh Source Research skill for metadata-slice extraction

update public.skills
set
  description = 'Extract title, issuing authority, version, publication date, and distribution line from early parsed pages with optional web gap-fill for title and authority.',
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
      "distribution_line": {"type": "string"},
      "confidence": {"type": "object"},
      "provenance": {"type": "object"},
      "web_sources": {"type": "array"}
    }
  }'::jsonb,
  prompts = '{
    "system": "Extract bibliographic metadata from the early pages of a parsed document: title, issuing authority, version, publication date, and distribution line.",
    "user_template": "Metadata slice extraction for source {{source_id}}."
  }'::jsonb
where skill_id = 'source-research'
  and version = '1.0';
