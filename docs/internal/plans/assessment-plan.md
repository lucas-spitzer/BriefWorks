# Assessment Sets Implementation Guide

## 1. Purpose

Assessment Sets are structured learning outputs generated from trusted source material. They are designed to test and reinforce learning across three levels:

1. **Flashcards** → Memorization
2. **Quizzes** → Understanding
3. **Scenarios** → Application

The system should generate Assessment Sets as structured JSON data first. Separately, a different UI will then render them into user-facing formats such as interactive study decks, quiz modules, decision exercises, Markdown exports, PDFs, Anki files, or HTML artifacts.

Assessment Sets should not be treated as static documents. They should be treated as reusable learning objects that can support study, review, export, remediation, and future adaptive learning.

---

## 2. Assessment Set Types

| Assessment Type | Learning Function | Purpose                                                                                          | Question It Answers     |
| --------------- | ----------------- | ------------------------------------------------------------------------------------------------ | ----------------------- |
| Flashcards      | Memorization      | Help the learner recall key terms, definitions, facts, lists, and relationships.                 | “Do I know this?”       |
| Quizzes         | Understanding     | Test whether the learner understands concepts, distinctions, causes, effects, and relationships. | “Do I understand this?” |
| Scenarios       | Application       | Force the learner to apply knowledge to a realistic problem, decision, or situation.             | “Can I use this?”       |

Assessment Sets should move the learner from recall to reasoning to judgment.

```text
Source Material
    ↓
Key Knowledge Extraction
    ↓
Flashcards
    ↓
Quizzes
    ↓
Scenarios
    ↓
Feedback / Review / Remediation
```

---

## 3. Flashcards

### Purpose

Flashcards support memorization. They are best for facts, definitions, doctrinal terms, formulas, sequences, acronyms, people, events, systems, and core concepts.

### Question Answered

> “Do I know this?”

### Best Uses

Flashcards are appropriate when the learner needs to rapidly recall information without deep context.

Examples:

* Key terms
* Definitions
* Acronyms
* Lists
* Doctrinal principles
* Historical dates
* System components
* Technical vocabulary
* Process steps

### Recommended Flashcard Subtypes

| Subtype            | Description                              |
| ------------------ | ---------------------------------------- |
| `basic`            | Standard front/back card                 |
| `term_definition`  | Term on front, definition on back        |
| `cloze`            | Fill-in-the-blank deletion               |
| `sequence`         | Recall ordered steps                     |
| `compare_contrast` | Distinguish between two related concepts |
| `image_label`      | Identify or label visual elements        |

### Example

```json
{
  "item_id": "uuid",
  "type": "flashcard",
  "subtype": "basic",
  "difficulty": "easy",
  "front": "What is combined arms?",
  "back": "The full integration of arms in such a way that to counteract one, the enemy becomes more vulnerable to another.",
  "source_chunk_ids": ["uuid"],
  "tags": ["doctrine", "fire-and-maneuver"]
}
```

---

## 4. Quizzes

### Purpose

Quizzes test understanding. They should determine whether the learner can explain, distinguish, connect, and reason through concepts.

### Question Answered

> “Do I understand this?”

### Best Uses

Quizzes are appropriate when the learner needs to demonstrate comprehension beyond memorization.

Examples:

* Conceptual distinctions
* Cause-and-effect relationships
* Best-answer questions
* Misconception checks
* Process understanding
* Comparison questions
* Interpretation of source material
* Reasoning through principles

### Recommended Quiz Subtypes

| Subtype                 | Description                          |
| ----------------------- | ------------------------------------ |
| `multiple_choice`       | One correct answer                   |
| `multiple_select`       | Multiple correct answers             |
| `true_false_correction` | True/false plus explanation          |
| `short_answer`          | Learner writes a brief answer        |
| `matching`              | Match terms to definitions           |
| `ordering`              | Put steps or events in sequence      |
| `assertion_reason`      | Evaluate claim and reasoning         |
| `compare_contrast`      | Explain differences between concepts |

### Example

```json
{
  "item_id": "uuid",
  "type": "quiz",
  "subtype": "multiple_choice",
  "difficulty": "medium",
  "question": "Which best describes the purpose of combined arms?",
  "choices": [
    "To use every weapon system at once",
    "To force the enemy into a dilemma",
    "To maximize indirect fire",
    "To avoid maneuver"
  ],
  "correct_answer": "To force the enemy into a dilemma",
  "explanation": "Combined arms creates complementary effects that make enemy reactions costly.",
  "source_chunk_ids": ["uuid"],
  "tags": ["understanding", "doctrine"]
}
```

---

## 5. Scenarios

### Purpose

Scenarios test application. They require the learner to use knowledge in context, make decisions, justify reasoning, and account for constraints.

### Question Answered

> “Can I use this?”

### Best Uses

Scenarios are appropriate when the learner needs to apply knowledge to a practical or realistic situation.

Examples:

* Tactical decision games
* Case studies
* Staff planning exercises
* Ethical decision-making
* Cyber incident response
* Intelligence analysis
* Leadership dilemmas
* Operational tradeoff analysis
* Technical troubleshooting

### Recommended Scenario Subtypes

| Subtype                  | Description                                     |
| ------------------------ | ----------------------------------------------- |
| `decision_prompt`        | Learner must make and justify a decision        |
| `case_study`             | Learner analyzes a real or fictional event      |
| `tactical_decision_game` | Military-style situation, mission, and decision |
| `branching_scenario`     | Learner choices affect follow-on conditions     |
| `staff_estimate`         | Learner produces structured analysis            |
| `red_team_blue_team`     | Adversarial or competitive reasoning exercise   |
| `aar_prompt`             | Learner conducts after-action review            |
| `rubric_response`        | Written response graded against criteria        |

### Example

```json
{
  "item_id": "uuid",
  "type": "scenario",
  "subtype": "decision_prompt",
  "difficulty": "hard",
  "situation": "Your platoon is advancing toward an enemy position with limited visibility and suspected machine-gun coverage.",
  "task": "Describe how you would apply combined arms to reduce enemy freedom of action.",
  "expected_response_elements": [
    "Suppress enemy position",
    "Use maneuver to exploit suppression",
    "Coordinate timing",
    "Account for terrain and visibility"
  ],
  "rubric": {
    "excellent": "Integrates fires, maneuver, timing, terrain, and enemy reaction.",
    "satisfactory": "Identifies suppression and maneuver but lacks detail.",
    "poor": "Lists assets without explaining integration."
  },
  "source_chunk_ids": ["uuid"],
  "tags": ["application", "tactical-decision"]
}
```

---

## 6. Assessment JSON Structure

Assessment Sets should be stored as canonical JSON data. The application can then render that JSON into web UI, Markdown, PDF, Anki, static HTML, or other formats.

The assessment object should preserve:

* Project relationship
* Source traceability
* Lesson relationship
* Assessment type
* Difficulty
* Prompt/question content
* Correct answer or expected answer
* Explanation
* Rubric where applicable
* Source chunk citations
* Tags and metadata

### Example Assessment Set JSON

Feel free to make adjustments as best fits our system. The following is a general example:

```json
{
  "assessment_set_id": "uuid",
  "project_id": "uuid",
  "source_ids": ["uuid"],
  "lesson_id": "uuid",
  "title": "Assessment Set: Combined Arms",
  "learning_goal": "Assess recall, understanding, and application of combined arms concepts.",
  "assessment_types": ["flashcards", "quizzes", "scenarios"],
  "items": [
    {
      "item_id": "uuid",
      "type": "flashcard",
      "subtype": "basic",
      "difficulty": "easy",
      "front": "What is combined arms?",
      "back": "The full integration of arms in such a way that to counteract one, the enemy becomes more vulnerable to another.",
      "source_chunk_ids": ["uuid"],
      "tags": ["doctrine", "fire-and-maneuver"]
    },
    {
      "item_id": "uuid",
      "type": "quiz",
      "subtype": "multiple_choice",
      "difficulty": "medium",
      "question": "Which best describes the purpose of combined arms?",
      "choices": [
        "To use every weapon system at once",
        "To force the enemy into a dilemma",
        "To maximize indirect fire",
        "To avoid maneuver"
      ],
      "correct_answer": "To force the enemy into a dilemma",
      "explanation": "Combined arms creates complementary effects that make enemy reactions costly.",
      "source_chunk_ids": ["uuid"],
      "tags": ["understanding", "doctrine"]
    },
    {
      "item_id": "uuid",
      "type": "scenario",
      "subtype": "decision_prompt",
      "difficulty": "hard",
      "situation": "Your platoon is advancing toward an enemy position with limited visibility and suspected machine-gun coverage.",
      "task": "Describe how you would apply combined arms to reduce enemy freedom of action.",
      "expected_response_elements": [
        "Suppress enemy position",
        "Use maneuver to exploit suppression",
        "Coordinate timing",
        "Account for terrain and visibility"
      ],
      "rubric": {
        "excellent": "Integrates fires, maneuver, timing, terrain, and enemy reaction.",
        "satisfactory": "Identifies suppression and maneuver but lacks detail.",
        "poor": "Lists assets without explaining integration."
      },
      "source_chunk_ids": ["uuid"],
      "tags": ["application", "tactical-decision"]
    }
  ]
}
```

---

## 7. Core Design Principle

Assessment Sets should be treated as structured learning systems, not static documents.

The correct architecture is:

```text
Canonical Assessment JSON
    ↓
Interactive Renderers
    ↓
Attempts and Feedback
    ↓
Exports and Review Artifacts
```

This lets Foundry generate one trusted assessment object and reuse it across multiple learning modes:

* Memorization
* Understanding
* Application
* Review
* Export
* Remediation

The canonical Assessment JSON should remain the source of truth. Every rendered output should be derived from that structure rather than manually rewritten as a separate artifact.
