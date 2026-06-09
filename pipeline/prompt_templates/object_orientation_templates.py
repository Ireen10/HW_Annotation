"""Templates for object_orientation task."""

from __future__ import annotations

from .register_structured import (
    EMPTY_QUESTION_INSTRUCTION,
    register_oe,
)

EN_DIRECT = [
    "Answer directly.",
    "Give a concise answer.",
    "Reply with only the orientation.",
    "State the orientation briefly.",
    "Use a short direct answer.",
]
EN_SENTENCE = [
    "Answer in a complete sentence.",
    "Reply in one full sentence.",
    "Give the answer as a full sentence.",
    "Respond with one complete sentence.",
    "Use a complete sentence format.",
]
ZH_DIRECT = [
    "直接回答即可。",
    "简要作答。",
    "只回答朝向。",
    "用简短答案回答。",
    "直接给出结果。",
]
ZH_SENTENCE = [
    "请用完整句子回答。",
    "请用一句完整的话回答。",
    "请以完整句式作答。",
    "请用完整陈述句回答。",
    "请用完整表达回答。",
]

register_oe(
    template_id="object_orientation.en.open_ended",
    introduction=[],
    stem=["What is the orientation of [A]?"],
    question_instruction_profiles={"direct": EN_DIRECT, "sentence": EN_SENTENCE, "free": EMPTY_QUESTION_INSTRUCTION},
    answer_templates_by_type={
        "direct": ["[X_EN]"],
        "sentence": ["[A] is oriented toward [X_EN]."],
        "free": ["[A] is oriented toward [X_EN]."],
    },
    enabled_instruction_types=["direct", "sentence", "free"],
)
register_oe(
    template_id="object_orientation.zh.open_ended",
    introduction=[],
    stem=["[A] 的朝向是什么？"],
    question_instruction_profiles={"direct": ZH_DIRECT, "sentence": ZH_SENTENCE, "free": EMPTY_QUESTION_INSTRUCTION},
    answer_templates_by_type={
        "direct": ["[X_ZH]"],
        "sentence": ["[A] 朝向[X_ZH]。"],
        "free": ["[A] 朝向[X_ZH]。"],
    },
    enabled_instruction_types=["direct", "sentence", "free"],
)
