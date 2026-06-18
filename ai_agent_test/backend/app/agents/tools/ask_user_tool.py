"""Ask-the-user tool helpers.

The ``ask_user`` tool lets the agent pause a run and put one or more questions to
the user, then resume with their answers. The actual pause/resume lives in the
WebSocket session (it owns the socket); this module just defines the question
schema and formats the collected answers into a result for the model.
"""

from typing import Any

from pydantic import BaseModel, Field

MAX_QUESTIONS = 10


class QuestionItem(BaseModel):
    """One question to put to the user."""

    question: str = Field(description="The question text.")
    options: list[str] = Field(
        default_factory=list,
        description="Optional suggested answers, shown as numbered choices.",
    )
    allow_custom: bool = Field(
        default=True,
        description="Whether the user may type a free-form answer instead of picking an option.",
    )


def format_answers(questions: list[dict[str, Any]], answers: list[dict[str, Any]]) -> str:
    """Render the collected answers as a readable Q/A transcript for the model."""
    lines: list[str] = []
    for i, q in enumerate(questions):
        a = answers[i] if i < len(answers) else {}
        if not isinstance(a, dict):
            a = {}
        ans = "(skipped)" if a.get("skipped") else str(a.get("answer", "")).strip() or "(no answer)"
        lines.append(f"Q: {q.get('question', '')}\nA: {ans}")
    return "\n\n".join(lines)
