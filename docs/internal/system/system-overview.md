# BriefWorks: System Overview & Tech Stack

## Rationale

### Introduction

BriefWorks is an educational content generation system that transforms raw knowledge into structured lessons, visual artifacts, assessment questions, and more. It is designed as a private, browser-based production studio for generating high-quality educational material from trusted source content.

BriefWorks consists of three core automation systems that work in tandem:

- **Intellex** — the intelligent knowledge base and source-processing system.
- **Mathesys** — the educational material generation system.
- **QnGen** — the question and assessment generation system.

Together, these systems allow a user to upload raw documents, media, and reference materials, convert those materials into a structured knowledge base, generate educational outputs from that knowledge, and produce questions that test the generated material.

The purpose of this document is to explain the architectural direction for BriefWorks and justify the technology stack selected for the project, with a focus on the React/Vite frontend, FastAPI backend, RQ job queue, Python workers, Supabase storage/database layer, pgvector search, and OpenAI LLM layer.

## System Vision

BriefWorks should function as a private educational production environment rather than a public SaaS application. The system is intended to be used primarily by its creator as a powerful personal tool for transforming source material into polished learning assets.

The ideal workflow is:

1. Upload source documents, media, or notes into BriefWorks.
2. Intellex ingests and organizes those materials.
3. Mathesys generates educational content (ebooks, narration audio) from the structured source.
4. The user reads the generated ebook and curates the knowledge wiki manually: unstructured reading notes are uploaded, structured by one LLM call, reviewed, and committed as canonical wiki entries (see [wiki-authoring-contract.md](../plans/wiki-authoring-contract.md)).
5. QnGen creates flashcards, quizzes, and scenarios from the curated wiki; the wiki itself is exportable as a JSON artifact.
6. The user reviews, edits, exports, and reuses the final learning package.

BriefWorks is not merely a repository of files, a command-line tool, or a collection of scripts. It is best understood as a web-based production studio for AI-assisted educational content creation.

## Production Pipeline

A **production run** is the unit of work that turns selected source files into artifacts and assessments. The user starts by choosing one or more source files, then chooses a desired artifact category and the specific artifact type(s) to generate. The backend assembles a pipeline, enqueues it on RQ/Redis, and a Python worker executes each stage in order.

### Example generation flow

1. **Select sources** — choose one or more uploaded source files from the workspace.
2. **Select artifact category** — pick the kind of output to produce. Today there is one category: **Document Narration**.
3. **Select artifact type(s)** — within Document Narration, four artifact types are available:
   - ElevenReader Script
   - Speechify Script
   - ElevenLabs Audio
   - Speechify Audio
4. **Intellex Stage** — ingest stages always run for each selected source: parse, normalize, trim boundaries, structure into chapters/sections, validate, chunk into NDR segments + `document_chapters`, then research metadata.
5. **Mathesys Stage** — artifact-generation stages run for each selected Document Narration type, using Intellex outputs as input. If `wiki_json` is selected, the curated wiki is exported as a JSON artifact for the source.
6. **Wiki authoring (manual, outside the pipeline)** — the user reads the generated ebook and curates the knowledge wiki: unstructured reading notes are uploaded, structured into candidate entries by one LLM call, reviewed, and committed as canonical `wiki_entries` (see [wiki-authoring-contract.md](../plans/wiki-authoring-contract.md)). This step has no production-run stage — it runs whenever the user is ready, independent of any run.
7. **QnGen Stage** — once a source has canonical wiki entries with evidence, the user can launch an assessment-only production run selecting review targets (flashcards, quizzes, and/or scenarios); the corresponding generate stages run per source (`generate-flashcards`, `generate-questions`, `generate-scenarios`), grouped by the source's persisted chapters.

### Pipeline rules

| Rule | Behavior |
|------|----------|
| Source selection | One or more source files may be included in a single production run. |
| Artifact categories | Document Narration is the only category implemented so far. |
| Artifact type selection | The user may select any combination of the four Document Narration artifact types, plus `wiki_json`. |
| Intellex ingest | Ingest stages (parse → normalize → trim → structure → validate → chunk → source-research) always run during the Intellex Stage, scoped to the selected source file(s). No extraction stage runs — ingest does not produce wiki entries. |
| Mathesys generation | Only the Mathesys stages that correspond to the user's selected artifact type(s) run, including `export-wiki-json` for the `wiki_json` target. |
| Wiki curation | Manual, outside any production run. The author uploads reading notes per chapter via the wiki authoring endpoints; entries are reviewed and committed to `wiki_entries` directly. |
| QnGen assessment | Runs when review targets are selected on a source that already has canonical wiki entries with evidence for that source. Each selected target appends its own generate stage step per source; chapter grouping comes from `document_chapters`, not from extraction. |

### Pipeline flowchart

```mermaid
flowchart TD
    subgraph user["User selection"]
        A[Select source file(s)]
        B[Choose artifact category]
        C[Document Narration]
        D{Select artifact type(s)}
        A --> B --> C --> D
        D --> E1[ElevenReader Script]
        D --> E2[Speechify Script]
        D --> E3[ElevenLabs Audio]
        D --> E4[Speechify Audio]
        D --> E5[Wiki JSON export]
    end

    subgraph intellex["Intellex Stage"]
        F[Parse with LlamaParse]
        N[Normalize document]
        T[Trim boundaries]
        S[Structure into chapters/sections]
        V[Validate structure]
        H[Chunk into NDR segments + document_chapters]
        G[Source research metadata slice]
        F --> N --> T --> S --> V --> H --> G
    end

    subgraph mathesys["Mathesys Stage"]
        G --> L1[ElevenReader Script stage]
        G --> L2[Speechify Script stage]
        G --> L3[ElevenLabs Audio stage]
        G --> L4[Speechify Audio stage]
        G --> L5[Export Wiki JSON stage]
    end

    subgraph authoring["Wiki authoring (manual, no run required)"]
        R[Read generated ebook]
        U[Upload chapter notes]
        X[LLM structuring + evidence linking]
        RV[Review draft entries]
        CM[Commit to canonical wiki_entries]
        R --> U --> X --> RV --> CM
    end

    subgraph qngen["QnGen Stage (assessment-only run)"]
        P1[generate-flashcards]
        P2[generate-questions]
        P3[generate-scenarios]
        P1 & P2 & P3 --> Out[flashcards / quizzes / scenarios]
    end

    E1 & E2 & E3 & E4 & E5 --> F
    G --> R
    CM --> qngen
```

Intellex ingest steps (`store`, `parse`, `normalize-document`, `trim-document-boundaries`, `structure-document`, `validate-structure`, `chunk`, `source-research`) run on every ingest. `parse` calls LlamaParse and records structured JSON on the stage run; `structure-document` produces the chapter/section model and `chunk` persists it as `document_chapters` plus `ndr_segments`. No stage extracts wiki knowledge — that is a manual step (`app/services/wiki_authoring.py`) the author runs after reading the generated ebook: unstructured notes go through one LLM structuring call, get enriched with slug/duplicate resolution and embedding-based evidence links into the source's `ndr_segments`, and are reviewed and committed to `wiki_entries` via `wiki_ingest_batches`. Mathesys only executes stages for the artifact types the user selected; `export-wiki-json` snapshots the source's canonical wiki entries into a downloadable JSON artifact (`wiki_json` target). `elevenreader-ebook` (v2) requires `document_chapters` and emits one audio-friendly EPUB per source — each chapter is a spine item with an h1 title, h2 subsection cues, and paragraph body text for manual ElevenReader upload. QnGen runs as an assessment-only production run once a source has canonical wiki entries with evidence; chapter grouping for the flashcard/question/scenario blueprints comes from `document_chapters`, not from any extraction stage.

## High-Level Architecture

```
React/Vite Frontend
        ↓
FastAPI Backend
        ↓
RQ Job Queue + Redis
        ↓
Python Workers
        ↓
Supabase Postgres + Supabase Storage + pgvector
        ↓
OpenAI LLM Layer
```

The frontend provides the user interface. FastAPI handles API requests, validation, authentication checks, and job creation. RQ and Redis manage background job dispatch. Python workers execute long-running AI and document-processing workflows. Supabase stores files, relational data, and vector embeddings. OpenAI provides the LLM and embedding layer.

## Final Recommendation

BriefWorks should be built as a private web-based educational production studio using:

- React + Vite for the frontend
- FastAPI for the backend API
- RQ + Redis for the initial job queue
- Python workers for long-running Intellex, Mathesys, and QnGen jobs
- Supabase for storage, Postgres, and pgvector
- OpenAI for LLM and embedding capabilities
- HTML + SVG + Canvas for visual educational artifact rendering
- GitHub for repository and version control

The final mental model is:

| Role | Component |
|------|-----------|
| Private educational production studio | BriefWorks |
| Library | Intellex |
| Teacher/designer | Mathesys |
| Examiner | QnGen |
| Studio interface | React/Vite |
| Coordination layer | FastAPI |
| Work-order system | RQ/Redis |
| Automation factory | Python workers |
| Memory and storage | Supabase |
| Intelligence layer | OpenAI |
