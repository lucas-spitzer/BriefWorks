-- RAG vector store: embeddings + similarity search for the Reader assistant.
--
-- Two retrieval channels back the assistant:
--   * ndr_segments  — raw chunked source text (recall, quotes, deep-linking)
--   * wiki_entries  — curated concept/term definitions (precision)
--
-- The Python API talks to these via the service role (RLS is bypassed), so the
-- workspace_id argument on each match function is the tenancy boundary. The
-- functions are SECURITY INVOKER and we revoke execute from anon/authenticated
-- so they can never be reached over the auto-generated REST API.

create extension if not exists vector with schema extensions;

-- ---------------------------------------------------------------------------
-- Embedding columns
-- 1536 dims = text-embedding-3-small, matching EXTRACT_EMBEDDING_MODEL so the
-- assistant and the extract-dedup path share one vector space.
-- ---------------------------------------------------------------------------

alter table public.ndr_segments
  add column if not exists embedding extensions.vector(1536);
alter table public.ndr_segments
  add column if not exists embedded_at timestamptz;

alter table public.wiki_entries
  add column if not exists embedding extensions.vector(1536);
alter table public.wiki_entries
  add column if not exists embedded_at timestamptz;

-- HNSW + cosine. OpenAI v3 vectors are L2-normalised, so cosine and dot-product
-- give identical rankings; cosine keeps the math readable (similarity = 1 - dist).
create index if not exists ndr_segments_embedding_idx
  on public.ndr_segments using hnsw (embedding extensions.vector_cosine_ops);
create index if not exists wiki_entries_embedding_idx
  on public.wiki_entries using hnsw (embedding extensions.vector_cosine_ops);

-- ---------------------------------------------------------------------------
-- match_ndr_segments — semantic search over chunked source text.
-- Returns everything the assistant needs to cite AND deep-link back into the
-- Reader: stable sequence_index (survives re-pagination) + chapter context.
-- ---------------------------------------------------------------------------

create or replace function public.match_ndr_segments(
  query_embedding extensions.vector(1536),
  p_workspace_id uuid,
  match_threshold double precision default 0.3,
  match_count integer default 8,
  p_source_ids uuid[] default null
)
returns table (
  id uuid,
  source_id uuid,
  sequence_index integer,
  kind text,
  text text,
  locator jsonb,
  chapter_title text,
  chapter_sequence integer,
  similarity double precision
)
language sql
stable
set search_path = public, extensions
as $$
  select
    s.id,
    s.source_id,
    s.sequence_index,
    s.kind,
    s.text,
    s.locator,
    c.title as chapter_title,
    c.sequence_index as chapter_sequence,
    1 - (s.embedding <=> query_embedding) as similarity
  from public.ndr_segments s
  left join lateral (
    select dc.title, dc.sequence_index
    from public.document_chapters dc
    where dc.source_id = s.source_id
      and s.id = any (dc.segment_ids)
    limit 1
  ) c on true
  where s.workspace_id = p_workspace_id
    and s.embedding is not null
    and (p_source_ids is null or s.source_id = any (p_source_ids))
    and 1 - (s.embedding <=> query_embedding) >= match_threshold
  order by s.embedding <=> query_embedding
  limit match_count;
$$;

-- ---------------------------------------------------------------------------
-- match_wiki_entries — semantic search over curated definitions.
-- ---------------------------------------------------------------------------

create or replace function public.match_wiki_entries(
  query_embedding extensions.vector(1536),
  p_workspace_id uuid,
  match_threshold double precision default 0.3,
  match_count integer default 6
)
returns table (
  id uuid,
  preferred_label text,
  canonical_slug text,
  definition text,
  importance text,
  similarity double precision
)
language sql
stable
set search_path = public, extensions
as $$
  select
    w.id,
    w.preferred_label,
    w.canonical_slug,
    w.definition,
    w.importance,
    1 - (w.embedding <=> query_embedding) as similarity
  from public.wiki_entries w
  where w.workspace_id = p_workspace_id
    and w.embedding is not null
    and w.status = 'canonical'
    and 1 - (w.embedding <=> query_embedding) >= match_threshold
  order by w.embedding <=> query_embedding
  limit match_count;
$$;

-- Lock the functions to the service role (matches the table-level revokes).
revoke execute on function public.match_ndr_segments(
  extensions.vector, uuid, double precision, integer, uuid[]
) from public, anon, authenticated;
revoke execute on function public.match_wiki_entries(
  extensions.vector, uuid, double precision, integer
) from public, anon, authenticated;
