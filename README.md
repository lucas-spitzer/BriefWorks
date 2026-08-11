# Arsenal

Arsenal is a private educational system with two surfaces in one SPA:

- **Foundry** — browser-based **educational production studio**. It transforms raw source documents into structured knowledge, listenable narration artifacts, and assessment questions through three coordinated automation systems running over a queued worker pipeline.
- **Academy** — learning surface for viewing and interacting with artifacts produced by Foundry.

| Foundry system | Role | Module |
|--------|------|--------|
| **Intellex** | The library — ingests, parses, researches, and deconstructs sources into a grounded knowledge base. | `intellex` |
| **Mathesys** | The teacher — turns the knowledge base into narration scripts and audio-ready artifacts. | `mathesys` |
| **QnGen** | The examiner — produces flashcards, quizzes, and scenarios from the material. | `qngen` |

---

## High-Level Architecture

```mermaid
flowchart TD
    subgraph client["Browser — React / Vite SPA"]
        UI[Foundry + Academy UI]
        SBJS[supabase-js auth]
    end

    subgraph api["FastAPI Backend"]
        AUTH[Auth dependency<br/>require_approved_user]
        ROUTERS[Routers<br/>workspaces · sources · stages<br/>production-runs · wiki<br/>artifacts · assessments]
        SVC[Services<br/>source_upload · queue<br/>production_runs]
    end

    subgraph queue["Job Queue"]
        REDIS[(Redis)]
        RQ[RQ Queue]
    end

    subgraph worker["Python Worker"]
        RUNNER[PipelineRunner]
        EXEC[Stage Executors]
    end

    subgraph data["Supabase"]
        PG[(Postgres + pgvector)]
        STORE[(Storage bucket: sources)]
    end

    subgraph ext["External APIs"]
        OPENAI[OpenAI<br/>LLM + embeddings]
    end

    UI --> SBJS
    SBJS -- access token --> ROUTERS
    ROUTERS --> AUTH
    AUTH -- verify + approval --> PG
    ROUTERS --> SVC
    SVC -- store file --> STORE
    SVC -- rows --> PG
    SVC -- enqueue --> RQ
    RQ <--> REDIS
    RQ -- dispatch job --> RUNNER
    RUNNER --> EXEC
    EXEC --> OPENAI
    EXEC -- read/write --> PG
    EXEC -- read/write artifacts --> STORE
    UI -- poll status --> ROUTERS
```

The browser authenticates with Supabase directly (`supabase-js`) and sends the resulting access token to FastAPI on every request. FastAPI verifies the token and an approval check before serving data. Long-running AI work never blocks the request: the API enqueues a job on Redis/RQ, and a separate Python worker executes the pipeline, writing results back to Postgres and Storage that the UI polls.

---

## Request & Authentication Flow

```mermaid
sequenceDiagram
    participant U as User
    participant SPA as React SPA
    participant SB as Supabase Auth
    participant API as FastAPI
    participant DB as Postgres

    U->>SPA: Open /app
    SPA->>SB: Sign in (OAuth / magic link)
    SB-->>SPA: Session + access token
    SPA->>API: Request + Authorization: Bearer <token>
    API->>SB: Validate token (get user)
    API->>DB: Check account is approved
    alt Approved
        API-->>SPA: 200 + data
    else Not approved
        API-->>SPA: 403 Forbidden
    end
```

Every endpoint except `/health` requires `Authorization: Bearer <supabase-access-token>`. The `require_approved_user` dependency rejects invalid sessions (401) and unapproved accounts (403). The backend uses the Supabase **service role** key for data access; the service role key is never exposed to the frontend.

---

## Source Upload & Ingest

Uploading a source automatically queues an **ingest-only** production run (the Intellex base pipeline). PDFs are the only supported source type today.

```mermaid
sequenceDiagram
    participant SPA as React SPA
    participant API as FastAPI
    participant ST as Supabase Storage
    participant DB as Postgres
    participant RQ as Redis / RQ
    participant W as Worker

    SPA->>API: POST /workspaces/{id}/sources (multipart file)
    API->>API: validate_source_upload<br/>(PDF magic bytes, size, filename)
    API->>ST: Upload file to sources bucket
    API->>DB: INSERT source (status=stored)
    API->>DB: INSERT production_run (target_artifacts=[])
    API->>RQ: enqueue orchestrate_production_run
    API-->>SPA: 202 source + run queued
    RQ->>W: dispatch job
    W->>W: Run base Intellex pipeline
    W->>DB: Update source status → ready
```

---

## The Production Pipeline

A **production run** is the unit of work that turns selected sources into artifacts and assessments. The user selects source files and a set of `target_artifacts`; the backend builds an ordered pipeline (`build_pipeline`) and enqueues it. The worker's `PipelineRunner` executes each step in order, updating the run's `pipeline` JSON after every step so the UI can show live progress.

### Pipeline composition

The pipeline always runs the **Intellex base steps**, then appends only the **optional stage steps** matching the requested `target_artifacts`. An empty `target_artifacts` list runs ingest only. When a source was already fully ingested in a prior run, those Intellex steps are skipped and the run proceeds directly to the requested artifact stages.

```mermaid
flowchart LR
    subgraph base["Intellex base — always runs"]
        S1[store] --> S2[parse] --> S3[prepare-document] --> S4[chunk] --> S5[source-research] --> S6[deconstruct-document] --> S7[extract-knowledge]
    end

    subgraph optional["Optional steps — appended per target_artifact"]
        direction TB
        M1[create-ebook]
        Q1[generate-flashcards]
        Q2[generate-questions]
        Q3[generate-scenarios]
    end

    S5 --> optional
```

| `target_artifact` | Pipeline step | Module | Output |
|-------------------|---------------|--------|--------|
| `electronic_book` | `create-ebook` | Mathesys | Electronic Book (one chapter-based EPUB for manual upload) |
| `flashcards` | `generate-flashcards` | QnGen | Flashcard set |
| `quizzes` | `generate-questions` | QnGen | Question set |
| `scenarios` | `generate-scenarios` | QnGen | Scenario set |

### Full pipeline execution

```mermaid
flowchart TD
    START([Production run queued]) --> RUNNING[status = running]

    subgraph intellex["Intellex Stage — always"]
        STORE[store<br/>verify storage paths]
        PARSE[parse<br/>LlamaParse → ParsedDocument]
        PREPARE[prepare-document<br/>learning content only]
        CHUNK[chunk<br/>NDR segments → Postgres]
        RESEARCH[source-research<br/>metadata slice + web gap-fill]
        DECON[deconstruct-document<br/>chapter/section segmentation]
        EXTRACT[extract-knowledge<br/>terms, concepts, insights]
        STORE --> PARSE --> PREPARE --> CHUNK --> RESEARCH --> DECON --> EXTRACT
    end

    subgraph mathesys["Mathesys Stage — selected only"]
        EBOOK[create-ebook]
    end

    subgraph qngen["QnGen Stage — selected only"]
        FLASH[generate-flashcards]
        QUIZ[generate-questions]
        SCEN[generate-scenarios]
    end

    RUNNING --> STORE
    EXTRACT -- promote knowledge --> WIKI[(wiki_entries)]
    EXTRACT --> mathesys
    mathesys -- EPUB --> ART[(artifacts + Storage)]
    mathesys --> qngen
    qngen --> ASSESS[(flashcards · quizzes · scenarios)]
    qngen --> DONE([status = completed])

    DONE -.failure at any step.-> FAILED([status = failed<br/>error recorded])
```

Each stage step runs once per selected source, recording an immutable `stage_run` row (inputs, output, model, token usage). Intellex `prepare-document` strips non-learning content; `deconstruct-document` persists chapter/section groupings in `document_chapters`; `extract-knowledge` promotes terms, concepts, and insights into `wiki_entries`. Mathesys `create-ebook` builds one simple EPUB per source from `document_chapters` (chapter titles, subsection headings, body text) for manual ElevenReader upload; the resulting `electronic_book` artifact lands in Storage with a signed URL served on download. QnGen stages promote `flashcards`, `quizzes`, and `scenarios`. If any step raises, the run is marked `failed`, the error is recorded, and in-flight sources are reset.

---

## Data Model

```mermaid
erDiagram
    workspaces ||--o{ sources : contains
    workspaces ||--o{ production_runs : has
    workspaces ||--o{ wiki_entries : has
    workspaces ||--o{ artifacts : has
    workspaces ||--o{ flashcards : has
    workspaces ||--o{ quizzes : has
    workspaces ||--o{ scenarios : has
    production_runs ||--o{ stage_runs : spawns
    production_runs }o--o{ sources : references
    sources ||--o{ ndr_segments : "chunked into"
    stages ||--o{ stage_runs : "executed as"

    workspaces {
        uuid id
        uuid owner_id
        text name
        text status
    }
    sources {
        uuid id
        text filename
        text storage_path
        text status
    }
    production_runs {
        uuid id
        uuid[] source_ids
        text[] target_artifacts
        jsonb pipeline
        text status
    }
    stage_runs {
        uuid id
        text stage_id
        text module
        jsonb output
        jsonb token_usage
    }
```

Stages are **versioned definitions** (`stage_id` + `version`, major.minor format such as `1.0` or `2.0`) seeded in Postgres; each execution creates a `stage_run` capturing the exact inputs, output, model, and token usage. Postgres has `pgvector` enabled for embedding-based search over NDR segments and wiki entries.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React + Vite + TypeScript, React Router |
| Auth | Supabase Auth (`supabase-js`) |
| Backend API | FastAPI (Python) |
| Job queue | RQ + Redis |
| Workers | Python (`PipelineRunner` + stage executors) |
| Database | Supabase Postgres + pgvector |
| File storage | Supabase Storage (`sources` bucket; per-source `parse/`, `structure/`, `narration/`, `artifacts/`) |
| LLM / embeddings | OpenAI |
| PDF parsing | LlamaParse (LlamaCloud, agentic tier) |

---

## Repository Layout

```text
Arsenal/
├── api/                      FastAPI backend + worker
│   └── app/
│       ├── routers/          HTTP endpoints
│       ├── services/         upload, queue, supabase, openai
│       ├── repositories/     Postgres data access
│       ├── intellex/         ingest, parsing, chunking, deconstruction stages
│       ├── mathesys/         narration / EPUB / SSML stages
│       ├── qngen/            flashcard / quiz / scenario stages
│       ├── worker/           PipelineRunner, stage executors, RQ jobs
│       └── pipeline.py       pipeline composition (base + optional steps)
├── app/                      React + Vite frontend
│   └── src/
│       ├── features/         auth + workspace providers
│       ├── components/foundry/   Foundry production UI
│       ├── components/academy/   Academy learning UI
│       └── lib/              API client + mappers
├── supabase/
│   └── setup/                greenfield SQL (01–04) + alter patches for existing DBs
├── docker/                   docker-compose (Redis)
└── docs/internal/            system overview & design notes
```

---

## Getting Started

Setup, environment variables, and the full endpoint reference live in [`api/README.md`](api/README.md). In short:

1. **Backend** — create a venv, install `api/requirements.txt`, populate `api/.env`, run `uvicorn app.main:app --reload --port 8000`.
2. **Queue + Worker** — start Redis (`docker compose up -d redis`), then run `python run_worker.py`.
3. **Database** — for a new Supabase project, run `01`–`04` in order (see [`supabase/setup/README.md`](supabase/setup/README.md)). Existing databases use the `alter-*.sql` patches in that same folder — see [`supabase/README.md`](supabase/README.md).
4. **Frontend** — point `VITE_API_BASE_URL` at the API and run the Vite dev server (see [`app/README.md`](app/README.md)).

For architectural rationale and the design narrative, see [`docs/internal/system/system-overview.md`](docs/internal/system/system-overview.md).
