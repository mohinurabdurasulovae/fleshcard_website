"""Evaluation scale and research quality criteria for flashcards.

Edit this file to change the criteria shown in the Evaluation page. Every criterion is
rated independently on the same five-level scale as the overall rating.
"""

RATING_SCALE = [
    {"level": 1, "label": "Excellent", "score": 5},
    {"level": 2, "label": "Very Good", "score": 4},
    {"level": 3, "label": "Acceptable", "score": 3},
    {"level": 4, "label": "Poor", "score": 2},
    {"level": 5, "label": "Unacceptable", "score": 1},
]

LEVEL_LABEL = {r["level"]: r["label"] for r in RATING_SCALE}


def level_to_score(level: int) -> int:
    """Level 1 (Excellent) -> 5 points … level 5 (Unacceptable) -> 1 point."""
    return 6 - int(level)


CRITERIA = [
    {
        "key": "accuracy",
        "label": "Factual accuracy",
        "description": "The question and answer are factually correct and free of errors.",
    },
    {
        "key": "faithfulness",
        "label": "Source faithfulness",
        "description": "The answer is grounded in, and traceable to, the cited part of the lecture notes.",
    },
    {
        "key": "clarity",
        "label": "Clarity",
        "description": "The question is unambiguous and the answer is easy to understand.",
    },
    {
        "key": "relevance",
        "label": "Relevance",
        "description": "The card targets an important concept of the course / topic rather than a trivial detail.",
    },
    {
        "key": "completeness",
        "label": "Completeness",
        "description": "The answer fully addresses the question without missing key information.",
    },
    {
        "key": "atomicity",
        "label": "Atomicity",
        "description": "The card tests a single, well-defined idea (one fact, formula or concept).",
    },
    {
        "key": "difficulty",
        "label": "Difficulty appropriateness",
        "description": "The difficulty suits university-level learners of this course.",
    },
    {
        "key": "usefulness",
        "label": "Learning usefulness",
        "description": "Studying this card would help a student understand and remember the material.",
    },
]

CARD_TYPES = [
    {"key": "definition", "label": "Definition"},
    {"key": "concept", "label": "Conceptual"},
    {"key": "explanation", "label": "Explanation"},
    {"key": "formula", "label": "Formula"},
    {"key": "comparison", "label": "Comparison"},
]
