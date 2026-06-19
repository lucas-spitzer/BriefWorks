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
3. Mathesys generates educational content from the source-grounded knowledge.
4. QnGen creates questions, quizzes, and assessments based on both the source material and the generated educational outputs.
5. The user reviews, edits, exports, and reuses the final learning package.

BriefWorks is not merely a repository of files, a command-line tool, or a collection of scripts. It is best understood as a web-based production studio for AI-assisted educational content creation.

## Production Pipeline

A **production run** is the unit of work that turns selected source files into artifacts and assessments. The user starts by choosing one or more source files, then chooses a desired artifact category and the specific artifact type(s) to generate. The backend assembles a pipeline, enqueues it on RQ/Redis, and a Python worker executes each stage in order.

### Example generation flow

1. **Select sources** — choose one or more uploaded source files from the workspace.
2. **Select artifact category** — pick the kind of output to produce. Today there is one category: **Document Narration**.
3. **Select artifact type(s)** — within Document Narration, all four artifact types are available as options:
   - ElevenReader Script
   - Speechify Script
   - ElevenLabs Audio
   - Speechify Audio
4. **Intellex Stage** — ingest stages always run for each selected source: parse, prepare learning-only content, chunk NDR segments, research metadata, then deconstruct into persisted chapters/sections.
5. **Mathesys Stage** — artifact-generation stages run for each selected Document Narration type, using Intellex outputs as input.
6. **QnGen Stage** — when the user selects review targets (flashcards, quizzes, and/or scenarios), the corresponding generate stages run per source (`generate-flashcards`, `generate-questions`, `generate-scenarios`).

### Pipeline rules

| Rule | Behavior |
|------|----------|
| Source selection | One or more source files may be included in a single production run. |
| Artifact categories | Document Narration is the only category implemented so far. |
| Artifact type selection | The user may select any combination of the four Document Narration artifact types. |
| Intellex deconstruction | Deconstruction stage(s) always run during the Intellex Stage, scoped to the selected source file(s). |
| Mathesys generation | Only the Mathesys stages that correspond to the user's selected artifact type(s) run. |
| QnGen assessment | Runs when review targets are selected. Requires intellex extract-knowledge (canonical wiki entries). Each selected target appends its own generate stage step per source. |

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
    end

    subgraph intellex["Intellex Stage"]
        F[Parse with LlamaParse]
        H[Prepare learning content GPT]
        I[Chunk NDR segments]
        G[Source research metadata slice]
        J[Deconstruct into chapters]
        K[Extract chapter knowledge]
        F --> H --> I --> G --> J --> K
    end

    subgraph mathesys["Mathesys Stage"]
        K{Selected artifact types}
        K --> L1[ElevenReader Script stage]
        K --> L2[Speechify Script stage]
        K --> L3[ElevenLabs Audio stage]
        K --> L4[Speechify Audio stage]
    end

    subgraph qngen["QnGen Stage (when review selected)"]
        P1[generate-flashcards]
        P2[generate-questions]
        P3[generate-scenarios]
        P1 & P2 & P3 --> N[flashcards / quizzes / scenarios]
    end

    E1 & E2 & E3 & E4 --> F
    J --> K
    L1 & L2 & L3 & L4 --> qngen
```

Intellex preparatory steps (`store`, `parse`, `prepare-document`, `chunk`, `source-research`, `deconstruct-document`, `extract-knowledge`) run on every ingest. `parse` calls LlamaParse and records structured JSON on the stage run. `prepare-document` owns all non-learning content removal; `deconstruct-document` persists chapter/section groupings; `extract-knowledge` runs one LLM call per chapter to populate `wiki_entries` with terms, concepts, and insights. Mathesys only executes stages for the artifact types the user selected. `elevenreader-ebook` (v2) requires `document_chapters` and emits one audio-friendly EPUB per source — each chapter is a spine item with an h1 title, h2 subsection cues, and paragraph body text for manual ElevenReader upload. QnGen runs when review targets are selected and requires canonical wiki entries from knowledge extraction.

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
