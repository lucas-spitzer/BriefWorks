from app.qngen.skills.shared.item_mapping import (
    assessment_item_to_scenario,
    normalize_difficulty,
)


def test_normalize_difficulty_passes_through_valid_values() -> None:
    assert normalize_difficulty("easy") == "easy"
    assert normalize_difficulty("medium") == "medium"
    assert normalize_difficulty("hard") == "hard"
    assert normalize_difficulty("HARD") == "hard"
    assert normalize_difficulty("  Medium  ") == "medium"


def test_normalize_difficulty_coerces_compound_and_freeform() -> None:
    # The exact value that violated scenarios_difficulty_check.
    assert normalize_difficulty("medium-hard") == "hard"
    assert normalize_difficulty("very easy") == "easy"
    assert normalize_difficulty("challenging") == "medium"
    assert normalize_difficulty(None) == "medium"
    assert normalize_difficulty(3) == "medium"


def test_scenario_mapper_emits_db_valid_difficulty() -> None:
    item = {
        "task": "Decide whether to pause.",
        "situation": "A night assault.",
        "difficulty": "medium-hard",
    }
    assert assessment_item_to_scenario(item)["difficulty"] == "hard"
