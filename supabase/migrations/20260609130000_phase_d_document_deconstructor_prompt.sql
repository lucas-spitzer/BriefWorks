-- Phase D: refresh Document Deconstructor skill metadata

update public.skills
set
  description = 'Identify essential terms and concepts required to understand a document and promote them to Wiki entries.',
  output_schema = '{
    "type": "object",
    "required": ["concepts"],
    "properties": {
      "concepts": {
        "type": "array",
        "items": {
          "type": "object",
          "required": ["term_label", "definition", "importance", "confidence"],
          "properties": {
            "term_label": {"type": "string"},
            "definition": {"type": "string"},
            "aliases": {"type": "array"},
            "prerequisite_labels": {"type": "array"},
            "pronunciation": {"type": "string"},
            "importance": {"type": "string"},
            "evidence_segment_ids": {"type": "array"},
            "confidence": {"type": "number"}
          }
        }
      }
    }
  }'::jsonb,
  prompts = '{
    "system": "Deconstruct the document into essential terms and concepts. Do not summarize or produce lesson narrative.",
    "user_template": "Extract concepts for source {{source_id}} from NDR segments."
  }'::jsonb
where skill_id = 'document-deconstructor'
  and version = '1.0.0';
