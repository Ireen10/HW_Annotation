"""Structured prompt templates with intro/stem/instruction contract."""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from .prompt_template import PromptRenderRecord
from .question_type import QuestionType


@dataclass(frozen=True, slots=True)
class AnswerInstructionProfile:
    instruction_type: str
    answer_templates: list[str]


@dataclass(frozen=True, slots=True)
class StructuredPromptTemplate:
    template_id: str
    question_type: QuestionType
    introduction: list[str] = field(default_factory=list)
    stem: list[str] = field(default_factory=list)
    question_instruction_profiles: dict[str, list[str]] = field(default_factory=dict)
    answer_profiles: dict[str, AnswerInstructionProfile] = field(default_factory=dict)
    enabled_answer_instruction_types: list[str] | None = None

    def render(
        self,
        *,
        question_bindings: dict[str, str] | None = None,
        answer_bindings: dict[str, str] | None = None,
    ) -> PromptRenderRecord:
        if not self.stem:
            raise ValueError(f"{self.template_id}: stem is empty")
        if not self.answer_profiles:
            raise ValueError(f"{self.template_id}: answer_profiles is empty")

        intro_idx, intro_line = _pick_optional(self.introduction)
        stem_idx, stem_line = _pick_required(self.stem)
        enabled = self.enabled_answer_instruction_types or list(self.answer_profiles.keys())
        if not enabled:
            raise ValueError(f"{self.template_id}: enabled instruction types is empty")
        answer_type = random.choice(enabled)
        profile = self.answer_profiles[answer_type]
        question_instruction_pool = self.question_instruction_profiles.get(answer_type, [])
        if answer_type not in self.question_instruction_profiles and self.question_instruction_profiles:
            raise KeyError(
                f"{self.template_id}: missing question_instruction pool for instruction_type={answer_type!r}"
            )
        inst_idx, inst_line = _pick_optional(question_instruction_pool)
        ans_idx, ans_line = _pick_required(profile.answer_templates)
        question_text = _join([intro_line, stem_line, inst_line])
        answer_text = ans_line.strip()

        return PromptRenderRecord(
            template_id=self.template_id,
            introduction_line=intro_line,
            stem_line=stem_line,
            question_instruction_line=inst_line,
            answer_instruction_type=answer_type,
            answer_line=ans_line,
            question_text=question_text,
            answer_text=answer_text,
            question_type=self.question_type,
            question_index=stem_idx,
            answer_index=ans_idx,
            introduction_index=intro_idx,
            question_instruction_index=inst_idx,
            question_bindings=question_bindings or {},
            answer_bindings=answer_bindings or {},
        )


class StructuredTemplateRegistry:
    def __init__(self) -> None:
        self._templates: dict[str, StructuredPromptTemplate] = {}

    def register(self, template: StructuredPromptTemplate) -> None:
        self._templates[template.template_id] = template

    def get(self, template_id: str) -> StructuredPromptTemplate:
        try:
            return self._templates[template_id]
        except KeyError as exc:
            raise KeyError(f"template not registered: {template_id}") from exc

    def list_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._templates.keys()))


STRUCTURED_TEMPLATE_REGISTRY = StructuredTemplateRegistry()


def _pick_optional(pool: list[str]) -> tuple[int, str]:
    if not pool:
        return -1, ""
    idx = random.randrange(len(pool))
    return idx, pool[idx].strip()


def _pick_required(pool: list[str]) -> tuple[int, str]:
    if not pool:
        raise ValueError("required template pool is empty")
    idx = random.randrange(len(pool))
    return idx, pool[idx].strip()


def _join(parts: list[str]) -> str:
    return " ".join([p.strip() for p in parts if p and p.strip()]).strip()
