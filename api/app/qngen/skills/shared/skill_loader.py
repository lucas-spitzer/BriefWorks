from __future__ import annotations

from pathlib import Path

_SKILLS_ROOT = Path(__file__).resolve().parents[1]


def load_skill_markdown(skill_name: str) -> str:
    """Load SKILL.md for a generator type (flashcards, questions, scenarios)."""
    skill_path = _SKILLS_ROOT / skill_name / "SKILL.md"

    if not skill_path.is_file():
        raise RuntimeError(f"Missing skill definition: {skill_path}")

    return skill_path.read_text(encoding="utf-8")
