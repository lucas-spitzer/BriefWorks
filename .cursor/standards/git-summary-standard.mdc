---
description: Review Git changes and write a short summary before pushing to GitHub
alwaysApply: false
---

# Git Summary Standard

Use this standard to summarize saved or committed code changes before pushing to GitHub.

## Task

Review the current Git changes and write:

1. A short **Git Summary**
2. A concise bullet list of what changed

## Inputs to Check

Use available Git context, such as:

```bash
git status
git diff
git diff --staged
git log --oneline -5
```

If changes are already committed, review the latest commit:

```bash
git show --stat
git show --summary
```

## Output Format

```md
Git Summary: <3 words or less>

- <short change>
- <short change>
- <short change>
```

## Rules

- Git Summary must be **3 words or less**
- Use clear, plain language
- Bullets must be short
- Use past tense
- Focus on meaningful changes, not every file
- Do not mention formatting-only changes unless important
- Do not include long explanations
- Do not include code snippets
- Do not invent changes
- If no changes are found, say:

```md
Git Summary: No changes

- No saved or committed changes found
```

## Good Examples

```md
Git Summary: Add Auth Guard

- Added protected route handling
- Checked user session before access
- Redirected unauthenticated users
```

```md
Git Summary: Refactor Prompts

- Renamed prompt builder utilities
- Split lesson and quiz prompts
- Added output validation notes
```

```md
Git Summary: Update Styling

- Added layout spacing rules
- Improved button states
- Cleaned unused CSS
```
