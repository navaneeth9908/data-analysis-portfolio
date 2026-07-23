"""Evaluation helpers for deterministic report Q&A demos."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import json
from pathlib import Path

from .answer import answer_question
from .models import Answer


@dataclass(frozen=True)
class EvaluationQuestion:
    """A single expected-answer check for a report Q&A corpus."""

    id: str
    question: str
    expected_answer_terms: tuple[str, ...]
    expected_citation: str


@dataclass(frozen=True)
class EvaluationResult:
    """Outcome for one deterministic evaluation question."""

    question: EvaluationQuestion
    answer: Answer
    matched_answer_terms: tuple[str, ...]
    expected_citation_found: bool
    failure_reasons: tuple[str, ...]

    @property
    def passed(self) -> bool:
        """Return whether the answer matched all expected terms and citation."""
        return not self.failure_reasons


def load_evaluation_questions(path: str | Path) -> tuple[EvaluationQuestion, ...]:
    """Load a JSON evaluation question set from disk."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = payload.get("questions", payload) if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError("evaluation file must contain a list or a questions list")

    questions: list[EvaluationQuestion] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("each evaluation question must be an object")
        questions.append(
            EvaluationQuestion(
                id=str(row["id"]),
                question=str(row["question"]),
                expected_answer_terms=tuple(str(term) for term in row["expected_answer_terms"]),
                expected_citation=str(row["expected_citation"]),
            )
        )
    return tuple(questions)


def evaluate_questions(
    questions: Sequence[EvaluationQuestion],
    report_paths: Sequence[str | Path],
    *,
    top_k: int = 3,
) -> tuple[EvaluationResult, ...]:
    """Run expected-answer checks against local report files."""
    results: list[EvaluationResult] = []
    for question in questions:
        answer = answer_question(question.question, report_paths, top_k=top_k)
        results.append(_score_answer(question, answer))
    return tuple(results)


def _score_answer(question: EvaluationQuestion, answer: Answer) -> EvaluationResult:
    answer_text = answer.answer.lower()
    matched_terms = tuple(
        term for term in question.expected_answer_terms if term.lower() in answer_text
    )
    missing_terms = tuple(
        term for term in question.expected_answer_terms if term not in matched_terms
    )
    citation_labels = {citation.label for citation in answer.citations}
    citation_found = question.expected_citation in citation_labels

    failure_reasons: list[str] = []
    if missing_terms:
        failure_reasons.append("missing answer terms: " + ", ".join(missing_terms))
    if not citation_found:
        failure_reasons.append(f"missing citation: {question.expected_citation}")

    return EvaluationResult(
        question=question,
        answer=answer,
        matched_answer_terms=matched_terms,
        expected_citation_found=citation_found,
        failure_reasons=tuple(failure_reasons),
    )
