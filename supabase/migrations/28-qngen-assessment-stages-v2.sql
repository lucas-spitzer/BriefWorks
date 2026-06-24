-- QnGen assessment stages v2: skill-based draft/critique orchestration with unified items output.

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
    'generate-flashcards',
    '2.0',
    'qngen',
    'Generate Flashcards',
    'Generate memorization flashcards via skill-based draft/critique orchestration, grounded in wiki concepts, evidence segments, and learning objectives.',
    array['text'],
    '{"type":"object","properties":{"source_id":{"type":"string"},"concept_count":{"type":"integer"},"batch_count":{"type":"integer"}}}'::jsonb,
    '{
      "type": "object",
      "required": ["items"],
      "properties": {
        "items": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["type", "subtype", "difficulty", "front", "back"],
            "properties": {
              "item_id": {"type": "string"},
              "type": {"type": "string"},
              "subtype": {"type": "string"},
              "difficulty": {"type": "string"},
              "wiki_ids_cited": {"type": "array"},
              "source_chunk_ids": {"type": "array"},
              "tags": {"type": "array"},
              "front": {"type": "string"},
              "back": {"type": "string"}
            }
          }
        },
        "flashcards": {"type": "array"}
      }
    }'::jsonb,
    '{
      "system": "Generate memorization flashcards from canonical wiki concepts using draft/critique skill orchestration.",
      "user_template": "Create flashcards for source {{source_id}}."
    }'::jsonb
  ),
  (
    'generate-questions',
    '2.0',
    'qngen',
    'Generate Questions',
    'Generate understanding checks via skill-based draft/critique orchestration, grounded in wiki concepts, evidence segments, and learning objectives.',
    array['text'],
    '{"type":"object","properties":{"source_id":{"type":"string"},"concept_count":{"type":"integer"},"batch_count":{"type":"integer"}}}'::jsonb,
    '{
      "type": "object",
      "required": ["items"],
      "properties": {
        "items": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["type", "subtype", "difficulty", "question", "correct_answer"],
            "properties": {
              "item_id": {"type": "string"},
              "type": {"type": "string"},
              "subtype": {"type": "string"},
              "difficulty": {"type": "string"},
              "wiki_ids_cited": {"type": "array"},
              "source_chunk_ids": {"type": "array"},
              "question": {"type": "string"},
              "choices": {"type": "array"},
              "correct_answer": {"type": "string"},
              "explanation": {"type": "string"}
            }
          }
        },
        "questions": {"type": "array"}
      }
    }'::jsonb,
    '{
      "system": "Generate quiz questions that test understanding using draft/critique skill orchestration.",
      "user_template": "Create quiz questions for source {{source_id}}."
    }'::jsonb
  ),
  (
    'generate-scenarios',
    '2.0',
    'qngen',
    'Generate Scenarios',
    'Generate application scenarios via skill-based draft/critique orchestration, grounded in essential wiki concepts and evidence segments.',
    array['text'],
    '{"type":"object","properties":{"source_id":{"type":"string"},"concept_count":{"type":"integer"},"batch_count":{"type":"integer"}}}'::jsonb,
    '{
      "type": "object",
      "required": ["items"],
      "properties": {
        "items": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["type", "subtype", "difficulty", "situation", "task"],
            "properties": {
              "item_id": {"type": "string"},
              "type": {"type": "string"},
              "subtype": {"type": "string"},
              "difficulty": {"type": "string"},
              "wiki_ids_cited": {"type": "array"},
              "source_chunk_ids": {"type": "array"},
              "situation": {"type": "string"},
              "task": {"type": "string"},
              "expected_response_elements": {"type": "array"},
              "rubric": {"type": "object"}
            }
          }
        },
        "scenarios": {"type": "array"}
      }
    }'::jsonb,
    '{
      "system": "Generate realistic application scenarios using draft/critique skill orchestration.",
      "user_template": "Create scenarios for source {{source_id}}."
    }'::jsonb
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
