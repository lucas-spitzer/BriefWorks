# BriefWorks API

FastAPI service for BriefWorks backend authorization, workspaces, sources, skills, and production-run orchestration.

## Local Setup

Create a virtual environment and install dependencies:

```bash
cd api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `api/.env` from `.env.example` and fill in the real values:

```bash
cp .env.example .env
```

Required variables:

```text
SUPABASE_URL
SUPABASE_PUBLISHABLE_KEY
SUPABASE_SERVICE_ROLE_KEY
FRONTEND_ORIGINS
REDIS_URL
SOURCES_BUCKET
RQ_QUEUE_NAME
OPENAI_API_KEY
OPENAI_MODEL
QNGEN_MODEL (default gpt-4o)
QNGEN_CONCEPT_BATCH_SIZE (default 8)
LLAMA_CLOUD_API_KEY
LLAMAPARSE_TIER (default agentic)
PREPARE_BATCH_PAGES (default 15)
TAVILY_API_KEY (optional, enables web gap-fill for Source Research title/authority)
SOURCE_RESEARCH_MAX_CHARS
```

Mathesys audio (text-to-speech) variables:

```text
ELEVENLABS_API_KEY (enables ElevenLabs Audio MP3 synthesis)
ELEVENLABS_VOICE_ID (default 21m00Tcm4TlvDq8ikWAM — pick a voice from your ElevenLabs voice library)
ELEVENLABS_REQUEST_TIMEOUT_SECONDS (default 600 — per-chunk read timeout for TTS API calls)
ELEVENLABS_MAX_RETRIES (default 3 — retries on timeout or 429/502/503/504)
ELEVENLABS_CHUNK_CHARS (default 2500 — max characters per TTS request)
PRODUCTION_RUN_JOB_TIMEOUT (default 2h — RQ worker timeout for full pipeline jobs)
ELEVENLABS_MODEL_ID (default eleven_v3)
ELEVENLABS_MAX_CHARS (default 200000 — cost guardrail; raise intentionally for large jobs)
ELEVENLABS_PRICE_PER_TOKEN (default 0.00018333 — subscription credit cost per character/token)
SPEECHIFY_API_KEY (optional; when unset, Speechify Audio runs emit a .ssml artifact instead of MP3)
SPEECHIFY_VOICE_ID (default george)
SPEECHIFY_MODEL (default simba-english)
SPEECHIFY_MAX_CHARS (default 200000)
```

Set `ELEVENLABS_API_KEY` and choose `ELEVENLABS_VOICE_ID` from your ElevenLabs
voice library to produce ElevenLabs Audio MP3s. Speechify Audio synthesizes MP3s
once `SPEECHIFY_API_KEY` is set; until then it stores clean SSML for later
synthesis.

`SUPABASE_ANON_KEY` may be used instead of `SUPABASE_PUBLISHABLE_KEY` for older Supabase projects.

Never put `SUPABASE_SERVICE_ROLE_KEY` in the Vite frontend.

Apply the Supabase migrations in `supabase/migrations/` in order before using the ingest endpoints (see [`supabase/README.md`](../supabase/README.md)).

## Run API

```bash
cd api
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

## Run Redis + Worker

BriefWorks uses Redis for the RQ job queue. Use **either** Docker or Homebrew.

### Option A — Docker (recommended if you use Docker Desktop)

From the repository root:

```bash
docker compose up -d redis
docker compose ps
```

Redis will be available at `redis://localhost:6379/0`.

Stop it later with:

```bash
docker compose down
```

### Option B — Homebrew Redis

```bash
brew install redis
brew services start redis
redis-cli ping   # should print PONG
```

### Start the worker

In a second terminal:

```bash
cd api
source .venv/bin/activate
python run_worker.py
```

The frontend should use:

```bash
VITE_API_BASE_URL="http://localhost:8000"
```

## Endpoints

All endpoints below except `/health` require:

```text
Authorization: Bearer <supabase-access-token>
```

### Health / auth

```text
GET /health
GET /me
```

### Workspaces

```text
GET    /workspaces
POST   /workspaces
GET    /workspaces/{workspace_id}
PATCH  /workspaces/{workspace_id}
DELETE /workspaces/{workspace_id}
```

### Sources

```text
GET    /workspaces/{workspace_id}/sources
POST   /workspaces/{workspace_id}/sources
GET    /workspaces/{workspace_id}/sources/{source_id}
GET    /workspaces/{workspace_id}/sources/{source_id}/segments
DELETE /workspaces/{workspace_id}/sources/{source_id}
```

`POST /sources` accepts `multipart/form-data` with a `file` field. Each successful upload automatically queues an ingest-only production run (Intellex pipeline through `deconstruct-document`). Redis and the RQ worker must be running.

### Skills

```text
GET /skills
GET /skills/{skill_id}/{version}
```

Optional query param: `?module=intellex|mathesys|qngen`

### Wiki

```text
GET /workspaces/{workspace_id}/wiki/entries
GET /workspaces/{workspace_id}/wiki/entries/{wiki_entry_id}
GET /workspaces/{workspace_id}/wiki/disputes
```

Optional query params on entries: `?status=canonical|disputed|open`, `?search=term`

### Assessments (QnGen)

```text
GET /workspaces/{workspace_id}/flashcards
GET /flashcards/{flashcard_id}
GET /workspaces/{workspace_id}/quizzes
GET /quizzes/{quiz_id}
GET /workspaces/{workspace_id}/scenarios
GET /scenarios/{scenario_id}
```

### Artifacts

```text
GET /workspaces/{workspace_id}/artifacts
GET /artifacts/{artifact_id}
GET /artifacts/{artifact_id}/download
```

`GET /download` returns a short-lived signed URL for the EPUB file.

### Production runs

```text
GET  /workspaces/{workspace_id}/production-runs
POST /workspaces/{workspace_id}/production-runs
GET  /production-runs/{production_run_id}
GET  /production-runs/{production_run_id}/skill-runs
GET  /skill-runs/{skill_run_id}
```

Example production run body:

```json
{
  "source_ids": ["uuid"],
  "target_artifacts": ["eleven_reader_script", "flashcards", "quizzes", "scenarios"]
}
```

`target_artifacts` is optional. An empty list runs Intellex ingest only (`store` through `deconstruct-document`).

Supported `target_artifacts` values:

- `eleven_reader_script` — Mathesys ElevenReader EBook (one chapter-based EPUB per source; requires `deconstruct-document`)
- `speechify_audio` — Mathesys Speechify Audio (MP3 via API; SSML when no key)
- `elevenlabs_audio` — Mathesys ElevenLabs Audio (MP3 via API)
- `flashcards` — QnGen generate-flashcards
- `quizzes` — QnGen generate-questions
- `scenarios` — QnGen generate-scenarios

Full pipeline worker behavior:

- always completes Intellex ingest (`store`, `parse`, `prepare-document`, `chunk`, `source-research`, `deconstruct-document`, `extract-knowledge`); reuses prior ingest/Intellex results when a source was already processed
- optionally runs Mathesys narration skills and QnGen skills based on `target_artifacts`
- promotes Wiki concepts, artifacts, and assessment entities
- marks production run `completed` when finished

## Tests

```bash
cd api
source .venv/bin/activate
pip install pymupdf
python -m pytest tests/
```
