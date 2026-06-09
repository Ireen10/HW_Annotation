"""Templates for allocentric_relation task."""

from __future__ import annotations

from .register_structured import (
    EMPTY_QUESTION_INSTRUCTION,
    register_mcq,
    register_oe,
)

EN_DIRECT = [
    "Answer directly.",
    "Give a concise answer.",
    "Reply with only the relation.",
    "State the relation briefly.",
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
    "只回答方位。",
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
    template_id="allocentric_relation.en.open_ended",
    introduction=["You are given two object placeholders in one image."],
    stem=["[VIEW_EN], where is [A] relative to [B]?"],
    question_instruction_profiles={"direct": EN_DIRECT, "sentence": EN_SENTENCE, "free": EMPTY_QUESTION_INSTRUCTION},
    answer_templates_by_type={
        "direct": ["[X_EN]"],
        "sentence": ["[VIEW_EN], [A] is [X_EN] relative to [B]."],
        "free": ["[VIEW_EN], [A] is [X_EN] relative to [B]."],
    },
    enabled_instruction_types=["direct", "sentence", "free"],
)
register_mcq(
    template_id="allocentric_relation.en.multiple_choice",
    introduction=["You are given two object placeholders in one image."],
    stem=["[VIEW_EN], choose where [A] is relative to [B]. Options: [OPTIONS_EN]"],
    question_instruction_profiles={"direct": EN_DIRECT, "sentence": EN_SENTENCE, "free": EMPTY_QUESTION_INSTRUCTION},
    answer_templates_by_type={
        "direct": ["[X_EN]"],
        "sentence": ["[VIEW_EN], the correct option is [X_EN]."],
        "free": ["[VIEW_EN], the correct option is [X_EN]."],
    },
    enabled_instruction_types=["direct", "sentence", "free"],
)

register_oe(
    template_id="allocentric_relation.zh.open_ended",
    introduction=["你会看到同一张图中的两个目标占位符。"],
    stem=["[VIEW_ZH]，[A] 相对 [B] 位于什么方位？"],
    question_instruction_profiles={"direct": ZH_DIRECT, "sentence": ZH_SENTENCE, "free": EMPTY_QUESTION_INSTRUCTION},
    answer_templates_by_type={
        "direct": ["[X_ZH]"],
        "sentence": ["[VIEW_ZH]，[A] 位于 [B] 的[X_ZH]。"],
        "free": ["[VIEW_ZH]，[A] 位于 [B] 的[X_ZH]。"],
    },
    enabled_instruction_types=["direct", "sentence", "free"],
)
register_mcq(
    template_id="allocentric_relation.zh.multiple_choice",
    introduction=["你会看到同一张图中的两个目标占位符。"],
    stem=["[VIEW_ZH]，请选择 [A] 相对 [B] 的方位。选项：[OPTIONS_ZH]"],
    question_instruction_profiles={"direct": ZH_DIRECT, "sentence": ZH_SENTENCE, "free": EMPTY_QUESTION_INSTRUCTION},
    answer_templates_by_type={
        "direct": ["[X_ZH]"],
        "sentence": ["[VIEW_ZH]，正确选项是[X_ZH]。"],
        "free": ["[VIEW_ZH]，正确选项是[X_ZH]。"],
    },
    enabled_instruction_types=["direct", "sentence", "free"],
)
