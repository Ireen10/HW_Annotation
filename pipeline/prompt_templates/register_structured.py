"""Structured template registration helpers (OpenSpatial-style contract)."""

from __future__ import annotations

from pipeline.qa.core import (
    AnswerInstructionProfile,
    QuestionType,
    STRUCTURED_TEMPLATE_REGISTRY,
    StructuredPromptTemplate,
)


EMPTY_QUESTION_INSTRUCTION: list[str] = []
DEFAULT_INSTRUCTION_TYPE = "default"
SENTENCE_QUESTION_INSTRUCTIONS: list[str] = [
    "Answer in a complete sentence.",
    "Reply in a full sentence.",
]


def register_oe(
    *,
    template_id: str,
    introduction: list[str] | None,
    stem: list[str],
    question_instruction_profiles: dict[str, list[str]] | None,
    answer_templates_by_type: dict[str, list[str]],
    enabled_instruction_types: list[str] | None = None,
) -> None:
    if not answer_templates_by_type:
        raise ValueError(f"{template_id}: answer_templates_by_type must be non-empty")
    q_profiles = dict(question_instruction_profiles or {})
    if not q_profiles:
        q_profiles = {k: EMPTY_QUESTION_INSTRUCTION for k in answer_templates_by_type.keys()}
    missing = [k for k in answer_templates_by_type.keys() if k not in q_profiles]
    if missing:
        raise ValueError(f"{template_id}: missing question_instruction_profiles for {missing}")
    answer_profiles = {
        key: AnswerInstructionProfile(
            instruction_type=key,
            answer_templates=list(templates),
        )
        for key, templates in answer_templates_by_type.items()
    }
    enabled = enabled_instruction_types or list(answer_profiles.keys())
    STRUCTURED_TEMPLATE_REGISTRY.register(
        StructuredPromptTemplate(
            template_id=template_id,
            question_type=QuestionType.OPEN_ENDED,
            introduction=list(introduction or []),
            stem=list(stem),
            question_instruction_profiles=q_profiles,
            answer_profiles=answer_profiles,
            enabled_answer_instruction_types=enabled,
        )
    )
