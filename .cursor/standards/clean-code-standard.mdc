---
description: Review and revise Python, TypeScript, and JavaScript code before pushing to GitHub
globs: **/*.{py,ts,tsx,js,jsx}
alwaysApply: false
---

# Clean Code Standard

Applies to: **Python, TypeScript, and JavaScript**

## Purpose

Use this standard when reviewing or revising code for clarity, maintainability, consistency, safety, and long-term project quality before pushing to GitHub.

The reviewer should improve code structure, naming, comments, and obvious quality issues while preserving runtime behavior unless explicitly instructed otherwise.

## Review Priorities

Review code in this order:

1. Correctness
2. Security and privacy
3. Clear naming
4. Simple structure
5. Type safety
6. Error handling
7. Comments and documentation
8. Style consistency
9. Performance only when relevant

Do not over-optimize or refactor working code without a clear reason.

## General Rules

- Preserve runtime behavior unless asked to change it.
- Do not add dependencies unless explicitly approved.
- Prefer simple, readable code over clever code.
- Prefer clear names over explanatory comments.
- Avoid broad refactors unless necessary.
- Remove dead code, unused imports, and unused variables.
- Keep functions focused on one responsibility.
- Keep files organized around one clear purpose.
- Avoid hidden side effects.
- Avoid duplicated logic when a small helper would improve clarity.
- Use existing project patterns when available.

## Naming Conventions

### General Naming Principles

Names should be:

- Clear
- Specific
- Searchable
- Consistent
- Honest about what the code does

Avoid:

- Vague names: `data`, `item`, `thing`, `stuff`, `obj`
- Excessive abbreviations: `usr`, `cfg`, `res`, `tmp`
- Misleading names
- Names that describe implementation instead of purpose
- Names that are too generic for domain objects

Acceptable short names:

- `i`, `j` for small loops
- `id` for identifiers
- `x`, `y` for coordinates
- `err` or `error` for caught errors
- Domain-standard abbreviations like `url`, `api`, `db`, `ui`, `llm`

### File Naming

#### TypeScript / JavaScript

Use **kebab-case** for most files:

```
source-ingestion-service.ts
lesson-generation-panel.tsx
auth-guard.ts
prompt-context-builder.ts
```

Use **PascalCase** only for React component files when the project already follows that convention:

```
SourceReviewPanel.tsx
LessonGenerationPanel.tsx
```

Use conventional suffixes where helpful:

```
*.service.ts
*.controller.ts
*.repository.ts
*.schema.ts
*.types.ts
*.utils.ts
*.test.ts
*.spec.ts
*.config.ts
```

Examples:

```
source.service.ts
source.repository.ts
lesson.types.ts
prompt-context.utils.ts
auth.middleware.ts
```

#### Python

Use **snake_case** for Python files:

```
source_ingestion_service.py
lesson_generator.py
prompt_context_builder.py
auth_guard.py
```

Use conventional suffixes where helpful:

```
*_service.py
*_repository.py
*_schema.py
*_types.py
*_utils.py
*_test.py
test_*.py
```

Examples:

```
source_service.py
source_repository.py
lesson_schema.py
prompt_context_utils.py
test_lesson_generator.py
```

### Function and Method Naming

#### TypeScript / JavaScript

Use **camelCase** for functions and methods:

```
buildPromptContext()
validateUploadedSource()
getApprovedKnowledgeBlocks()
createLessonDraft()
```

Use verb-first names for functions that do work:

```
createUser()
fetchSourceById()
validateInput()
generateLesson()
normalizeDocumentText()
```

Use boolean-style names for boolean functions:

```
isApproved()
hasPermission()
canGenerateLesson()
shouldRetryRequest()
```

#### Python

Use **snake_case** for functions and methods:

```
build_prompt_context()
validate_uploaded_source()
get_approved_knowledge_blocks()
create_lesson_draft()
```

Use verb-first names for actions:

```
create_user()
fetch_source_by_id()
validate_input()
generate_lesson()
normalize_document_text()
```

Use boolean-style names for boolean functions:

```
is_approved()
has_permission()
can_generate_lesson()
should_retry_request()
```

### Variable Naming

#### TypeScript / JavaScript

Use **camelCase**:

```
approvedBlocks
sourceDocument
generationOptions
authenticatedUser
```

#### Python

Use **snake_case**:

```
approved_blocks
source_document
generation_options
authenticated_user
```

Prefer specific names:

Bad:

```typescript
const data = await fetchSource();
```

Good:

```typescript
const sourceDocument = await fetchSource();
```

Bad:

```python
result = generate()
```

Good:

```python
lesson_draft = generate_lesson_draft()
```

### Class, Type, and Interface Naming

#### TypeScript / JavaScript

Use **PascalCase** for classes, types, interfaces, React components, and schemas:

```
SourceDocument
LessonGenerationOptions
PromptContextBuilder
SourceReviewPanel
CreateLessonRequestSchema
```

Interface names should not require an `I` prefix unless the project already uses that convention.

Prefer:

```typescript
interface UserProfile {}
```

Avoid:

```typescript
interface IUserProfile {}
```

#### Python

Use **PascalCase** for classes:

```
SourceDocument
LessonGenerator
PromptContextBuilder
```

Use **snake_case** for instance attributes:

```
self.source_document
self.generation_options
```

### Constant Naming

Use **UPPER_SNAKE_CASE** for true constants in both ecosystems:

```typescript
const MAX_RETRY_COUNT = 3;
const DEFAULT_MODEL_NAME = "gpt-4.1";
```

```python
MAX_RETRY_COUNT = 3
DEFAULT_MODEL_NAME = "gpt-4.1"
```

Use normal variable naming for values that are only locally assigned and not true constants.

### Object and Data Shape Naming

Use domain-specific names for objects.

Bad:

```typescript
const payload = { id, text };
```

Better:

```typescript
const lessonRequest = { sourceId, promptText };
```

Bad:

```python
params = {"id": id, "text": text}
```

Better:

```python
lesson_request = {"source_id": source_id, "prompt_text": prompt_text}
```

Use names that reveal the object's role:

```
sourceMetadata
lessonGenerationRequest
approvedKnowledgeBlock
userAuthContext
```

```
source_metadata
lesson_generation_request
approved_knowledge_block
user_auth_context
```

## TypeScript and JavaScript Standards

### Type Safety

For TypeScript:

- Avoid `any` unless absolutely necessary.
- Prefer explicit types at system boundaries.
- Use `unknown` instead of `any` when validating external input.
- Define shared domain types in `*.types.ts`.
- Keep API request and response types clear.
- Avoid large, deeply nested anonymous object types.

Good:

```typescript
type LessonGenerationRequest = {
  sourceId: string;
  maxBlocks: number;
};
```

Avoid:

```typescript
function generateLesson(request: any) {}
```

### Imports and Exports

- Remove unused imports.
- Prefer named exports for shared utilities.
- Keep imports grouped and readable.
- Avoid circular dependencies.
- Avoid large barrel files if they obscure dependencies.

### React

For React code:

- Components should have clear names.
- Keep components focused.
- Extract complex logic into hooks or helpers.
- Avoid deeply nested JSX.
- Avoid unnecessary state.
- Keep server-only logic out of client components.
- Name hooks with `use`.

Examples:

```
useSourceDocuments()
useLessonGeneration()
useAuthSession()
```

## Python Standards

### Type Hints

Use type hints for:

- Public functions
- Complex functions
- Service methods
- Data transformation functions
- External API boundaries

Example:

```python
def build_prompt_context(blocks: list[KnowledgeBlock]) -> str:
    ...
```

Avoid overcomplicating types when they reduce readability.

### Imports

- Remove unused imports.
- Use standard library imports first.
- Then third-party imports.
- Then local imports.
- Avoid wildcard imports.

Good:

```python
import os
from pathlib import Path

from pydantic import BaseModel

from app.sources import SourceDocument
```

Avoid:

```python
from module import *
```

### Python Structure

- Keep functions small and focused.
- Avoid deeply nested logic.
- Prefer early returns for invalid states.
- Avoid mutable default arguments.
- Use dataclasses or Pydantic models for structured data when appropriate.
- Do not hide important behavior in global state.

Bad:

```python
def add_item(item, items=[]):
    items.append(item)
    return items
```

Good:

```python
def add_item(item, items=None):
    if items is None:
        items = []
    items.append(item)
    return items
```

## Commenting and Documentation

### Commenting Principles

Comments should explain:

- Why the code exists
- Important assumptions
- Security or privacy concerns
- Performance concerns
- Non-obvious business logic
- Temporary work or known issues

Do not comment obvious syntax.

Bad:

```typescript
// Add one to count
count++;
```

Good:

```typescript
// Limit retries to avoid repeated API calls during provider outages.
retryCount++;
```

### Doc Comments

Add short doc comments to exported, public, reused, or complex code.

TypeScript / JavaScript:

```typescript
/**
 * Builds source context for AI generation from approved knowledge blocks.
 */
export function buildPromptContext(blocks: KnowledgeBlock[]) {
  ...
}
```

Python:

```python
def build_prompt_context(blocks: list[KnowledgeBlock]) -> str:
    """Build source context for AI generation from approved knowledge blocks."""
    ...
```

### Inline Comments

Use inline comments only for:

- Complex transformations
- Domain-specific decisions
- Security-sensitive logic
- Performance-sensitive logic
- External API assumptions
- AI/model prompting boundaries
- Temporary workarounds

Example:

```typescript
// SECURITY: Only approved blocks are sent to the model to prevent unreviewed
// source material from reaching user-facing output.
const approvedBlocks = blocks.filter((block) => block.status === "approved");
```

```python
# SECURITY: Only approved blocks are sent to the model to prevent unreviewed
# source material from reaching user-facing output.
approved_blocks = [block for block in blocks if block.status == "approved"]
```

### Standard Tags

Use these tags consistently:

```
TODO: Planned improvement.
FIXME: Known broken behavior.
HACK: Temporary workaround.
NOTE: Important non-obvious detail.
SECURITY: Security or privacy-sensitive decision.
PERF: Performance-sensitive decision.
```

## Error Handling

### General

- Handle expected failure modes explicitly.
- Do not silently swallow errors.
- Avoid generic error messages.
- Preserve useful debugging context.
- Do not expose secrets or private data in errors.
- Validate external input before use.
- Fail safely when dealing with auth, permissions, files, or AI output.

Bad:

```typescript
catch (error) {
  console.log(error);
}
```

Better:

```typescript
catch (error) {
  logger.error("Failed to generate lesson draft", { sourceId, error });
  throw new Error("Unable to generate lesson draft.");
}
```

Bad:

```python
except Exception:
    pass
```

Better:

```python
except Exception as error:
    logger.exception("Failed to generate lesson draft for source_id=%s", source_id)
    raise LessonGenerationError("Unable to generate lesson draft") from error
```

## Security and Privacy

Review carefully any code involving:

- Authentication
- Authorization
- Private user data
- Uploaded files
- Environment variables
- API keys
- Database access
- Server-only logic
- AI prompts using private source material
- User-generated content
- External APIs

Rules:

- Never expose secrets to the client.
- Never log API keys, tokens, passwords, or private documents.
- Validate user input.
- Check authorization before accessing private records.
- Keep server-only code separate from client code.
- Treat uploaded files as untrusted input.
- Avoid sending unnecessary private data to AI models.
- Prefer least-privilege access patterns.

## AI / LLM Workflow Code

For AI-related code:

- Clearly separate prompt construction, model calls, validation, and persistence.
- Name prompt-building functions clearly.
- Track what source material is sent to the model.
- Do not send full private documents unless required.
- Validate model output before using it.
- Handle malformed model responses.
- Comment security/privacy boundaries.
- Keep user-visible output separate from internal reasoning or intermediate data.

Preferred names:

```
buildPromptContext()
createLessonPrompt()
validateModelOutput()
parseGeneratedLesson()
```

```
build_prompt_context()
create_lesson_prompt()
validate_model_output()
parse_generated_lesson()
```

## Testing Review

When reviewing tests:

- Test names should describe behavior.
- Avoid vague test names like `test1`.
- Tests should cover normal cases, edge cases, and failure cases.
- Avoid brittle tests that depend on implementation details.
- Use clear arrange/act/assert structure when helpful.

TypeScript / JavaScript:

```typescript
it("rejects lesson generation when the source is not approved", () => {
  ...
});
```

Python:

```python
def test_rejects_lesson_generation_when_source_is_not_approved():
    ...
```

## AI Code Review Instruction

Review and revise the provided **Python, TypeScript, and JavaScript** code according to this standard before pushing to GitHub.

Requirements:

1. Preserve runtime behavior unless explicitly instructed otherwise.
2. Do not add dependencies unless explicitly approved.
3. Improve unclear names for files, functions, variables, objects, classes, and types.
4. Add or improve comments only where they clarify intent, constraints, risk, or non-obvious logic.
5. Remove noisy comments, dead code, unused imports, and unused variables.
6. Improve type safety where low-risk and obvious.
7. Improve error handling where failure modes are clear.
8. Flag security, privacy, or AI workflow risks.
9. Avoid broad refactors.
10. Summarize the changes made and list any larger issues that should be handled separately.
