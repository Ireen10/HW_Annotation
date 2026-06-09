"""Templates for image_relative_position task."""

from __future__ import annotations

from .register_structured import (
    EMPTY_QUESTION_INSTRUCTION,
    register_mcq,
    register_oe,
)

EN_DIRECT = [
    "Answer directly.",
    "Give a concise answer.",
    "Reply with only the direction.",
    "State the direction briefly.",
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
    "只回答方向。",
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
    template_id="image_relative_position.en.open_ended",
    introduction=None,
    stem=[
        "In the image plane, where is [A] relative to [B]? Judge only by left/right/up/down and diagonal directions."
    ],
    question_instruction_profiles={"direct": EN_DIRECT, "sentence": EN_SENTENCE, "free": EMPTY_QUESTION_INSTRUCTION},
    answer_templates_by_type={
        "direct": ["[X_EN]"],
        "sentence": ["[A] is [X_EN] relative to [B] in the image plane."],
        "free": ["[A] is [X_EN] relative to [B] in the image plane."],
    },
    enabled_instruction_types=["direct", "sentence", "free"],
)
register_mcq(
    template_id="image_relative_position.en.multiple_choice",
    introduction=None,
    stem=[
        "In the image plane, choose the relative direction of [A] with respect to [B]. Options: [OPTIONS_EN]"
    ],
    question_instruction_profiles={"direct": EN_DIRECT, "sentence": EN_SENTENCE, "free": EMPTY_QUESTION_INSTRUCTION},
    answer_templates_by_type={
        "direct": ["[X_EN]"],
        "sentence": ["The correct option is [X_EN]."],
        "free": ["The correct option is [X_EN]."],
    },
    enabled_instruction_types=["direct", "sentence", "free"],
)

register_oe(
    template_id="image_relative_position.zh.open_ended",
    introduction=None,
    stem=["在图像平面内，[A] 相对 [B] 位于什么方向？仅按上下左右及对角方向判断。"],
    question_instruction_profiles={"direct": ZH_DIRECT, "sentence": ZH_SENTENCE, "free": EMPTY_QUESTION_INSTRUCTION},
    answer_templates_by_type={
        "direct": ["[X_ZH]"],
        "sentence": ["在图像平面内，[A] 位于 [B] 的[X_ZH]。"],
        "free": ["在图像平面内，[A] 位于 [B] 的[X_ZH]。"],
    },
    enabled_instruction_types=["direct", "sentence", "free"],
)
register_mcq(
    template_id="image_relative_position.zh.multiple_choice",
    introduction=None,
    stem=["在图像平面内，请选择 [A] 相对 [B] 的方向。选项：[OPTIONS_ZH]"],
    question_instruction_profiles={"direct": ZH_DIRECT, "sentence": ZH_SENTENCE, "free": EMPTY_QUESTION_INSTRUCTION},
    answer_templates_by_type={
        "direct": ["[X_ZH]"],
        "sentence": ["正确选项是[X_ZH]。"],
        "free": ["正确选项是[X_ZH]。"],
    },
    enabled_instruction_types=["direct", "sentence", "free"],
)
