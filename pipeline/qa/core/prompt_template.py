"""Prompt template render records (unrendered placeholder aware)."""

from __future__ import annotations

from dataclasses import dataclass, field

from .question_type import QuestionType


@dataclass(frozen=True, slots=True)
class PromptRenderRecord:
    template_id: str
    introduction_line: str
    stem_line: str
    question_instruction_line: str
    answer_instruction_type: str
    answer_line: str
    question_text: str
    answer_text: str
    question_type: QuestionType
    question_index: int = -1
    answer_index: int = -1
    introduction_index: int = -1
    question_instruction_index: int = -1
    question_bindings: dict[str, str] = field(default_factory=dict)
    answer_bindings: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "template_id": self.template_id,
            "introduction_line": self.introduction_line,
            "stem_line": self.stem_line,
            "question_instruction_line": self.question_instruction_line,
            "answer_instruction_type": self.answer_instruction_type,
            "answer_line": self.answer_line,
            "question_text": self.question_text,
            "answer_text": self.answer_text,
            "question_type": self.question_type.value,
            "question_index": self.question_index,
            "answer_index": self.answer_index,
            "introduction_index": self.introduction_index,
            "question_instruction_index": self.question_instruction_index,
            "question_bindings": dict(self.question_bindings),
            "answer_bindings": dict(self.answer_bindings),
        }
