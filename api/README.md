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
TAVILY_API_KEY (optional, enables web gap-fill for Source Research)
SOURCE_RESEARCH_MAX_CHARS
```

`SUPABASE_ANON_KEY` may be used instead of `SUPABASE_PUBLISHABLE_KEY` for older Supabase projects.

Never put `SUPABASE_SERVICE_ROLE_KEY` in the Vite frontend.

Apply the Supabase migrations in `supabase/migrations/` (Phase A through F) before using the ingest endpoints.

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

`POST /sources` accepts `multipart/form-data` with a `file` field.

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

`target_artifacts` is optional. An empty list runs Intellex ingest only (`store` through `document-deconstructor`).

Supported `target_artifacts` values:

- `eleven_reader_script` — Mathesys ElevenReader EPUB
- `flashcards` — QnGen flashcard-gen
- `quizzes` — QnGen quiz-gen
- `scenarios` — QnGen scenario-gen

Full pipeline worker behavior:

- always completes Intellex ingest (`store`, `parse`, `source-research`, `chunk`, `document-deconstructor`)
- optionally runs Mathesys `eleven-reader-script` and QnGen skills based on `target_artifacts`
- promotes Wiki concepts, artifacts, and assessment entities
- marks production run `completed` when finished

## Tests

```bash
cd api
source .venv/bin/activate
pip install pymupdf
python -m pytest tests/
```
