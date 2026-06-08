"""Metadata builders for unrendered QA turns."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TurnMetadata:
    item_id: str
    task_name: str
    template_id: str
    question_type: str
    introduction_pattern: str
    question_pattern: str
    question_instruction_pattern: str
    answer_pattern: str
    question_bindings: dict[str, str]
    answer_bindings: dict[str, str]
    mark_spec: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "item_id": self.item_id,
            "task_name": self.task_name,
            "template_id": self.template_id,
            "question_type": self.question_type,
            "introduction_pattern": self.introduction_pattern,
            "question_pattern": self.question_pattern,
            "question_instruction_pattern": self.question_instruction_pattern,
            "answer_pattern": self.answer_pattern,
            "question_bindings": dict(self.question_bindings),
            "answer_bindings": dict(self.answer_bindings),
            "mark_spec": dict(self.mark_spec),
        }
