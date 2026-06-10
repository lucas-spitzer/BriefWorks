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
4. **Intellex Stage** — deconstruction skill(s) always run for each corresponding source file, producing a structured knowledge base (essential terms, concepts, and wiki entries) grounded in the parsed source material.
5. **Mathesys Stage** — artifact-generation skills run for each selected Document Narration type, using Intellex outputs as input.
6. **QnGen Stage** — all QnGen skills always run, producing three assessment outputs: a **flashcard set**, a **question set**, and a **scenario set**.

### Pipeline rules

| Rule | Behavior |
|------|----------|
| Source selection | One or more source files may be included in a single production run. |
| Artifact categories | Document Narration is the only category implemented so far. |
| Artifact type selection | The user may select any combination of the four Document Narration artifact types. |
| Intellex deconstruction | Deconstruction skill(s) always run during the Intellex Stage, scoped to the selected source file(s). |
| Mathesys generation | Only the Mathesys skills that correspond to the user's selected artifact type(s) run. |
| QnGen assessment | All QnGen skills always run at the end of every production run, regardless of which artifact types were selected. |

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
        F[Ingest & parse sources]
        G[Source research]
        H[Chunk into NDR segments]
        I[Document Deconstructor per source]
        F --> G --> H --> I
    end

    subgraph mathesys["Mathesys Stage"]
        J{Selected artifact types}
        J --> K1[ElevenReader Script skill]
        J --> K2[Speechify Script skill]
        J --> K3[ElevenLabs Audio skill]
        J --> K4[Speechify Audio skill]
    end

    subgraph qngen["QnGen Stage (always runs)"]
        O[Run all QnGen skills]
        O --> L[Flashcard set]
        O --> M[Question set]
        O --> N[Scenario set]
    end

    E1 & E2 & E3 & E4 --> F
    I --> J
    K1 & K2 & K3 & K4 --> O
```

Intellex preparatory steps (ingest, parse, chunk, source research) run before deconstruction on every run. Mathesys only executes skills for the artifact types the user selected. QnGen always produces all three assessment sets as the final stage.

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
