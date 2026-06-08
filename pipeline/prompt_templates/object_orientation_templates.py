"""Templates for object_orientation task."""

from __future__ import annotations

from .register_structured import (
    EMPTY_QUESTION_INSTRUCTION,
    SENTENCE_QUESTION_INSTRUCTIONS,
    register_oe,
)

INTRODUCTION = [
    "You are given one image with an orientation-participating object.",
]

STEM = [
    "Describe the orientation of [A] in the current image context.",
]

QUESTION_INSTRUCTION_PROFILES = {
    "direct": EMPTY_QUESTION_INSTRUCTION,
    "sentence": SENTENCE_QUESTION_INSTRUCTIONS,
}

ANSWER_TEMPLATES_BY_TYPE = {
    "direct": ["[X]"],
    "sentence": ["[X]"],
}

register_oe(
    template_id="object_orientation.open_ended",
    introduction=INTRODUCTION,
    stem=STEM,
    question_instruction_profiles=QUESTION_INSTRUCTION_PROFILES,
    answer_templates_by_type=ANSWER_TEMPLATES_BY_TYPE,
    enabled_instruction_types=["direct", "sentence"],
)
