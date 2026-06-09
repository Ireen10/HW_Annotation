"""Templates for image_position task."""

from __future__ import annotations

from .register_structured import (
    EMPTY_QUESTION_INSTRUCTION,
    register_mcq,
    register_oe,
)

EN_DIRECT = [
    "Answer directly.",
    "Give a concise answer.",
    "Reply with only the position.",
    "State the position briefly.",
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
    "只回答位置。",
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

# English: with criterion (90%)
register_oe(
    template_id="image_position.en.with_criterion.open_ended",
    introduction=["You are given one object placeholder in an image."],
    stem=[
        "Using the 3x3 image-plane criterion (left/center/right and top/middle/bottom by bbox center), where is [A] in the image?"
    ],
    question_instruction_profiles={"direct": EN_DIRECT, "sentence": EN_SENTENCE, "free": EMPTY_QUESTION_INSTRUCTION},
    answer_templates_by_type={
        "direct": ["[X_EN]"],
        "sentence": ["It is [X_EN]."],
        "free": ["It is [X_EN]."],
    },
    enabled_instruction_types=["direct", "sentence", "free"],
)
register_mcq(
    template_id="image_position.en.with_criterion.multiple_choice",
    introduction=["You are given one object placeholder in an image."],
    stem=[
        "Using the 3x3 image-plane criterion (left/center/right and top/middle/bottom by bbox center), choose the position of [A]. Options: [OPTIONS_EN]"
    ],
    question_instruction_profiles={"direct": EN_DIRECT, "sentence": EN_SENTENCE, "free": EMPTY_QUESTION_INSTRUCTION},
    answer_templates_by_type={
        "direct": ["[X_EN]"],
        "sentence": ["The correct option is [X_EN]."],
        "free": ["The correct option is [X_EN]."],
    },
    enabled_instruction_types=["direct", "sentence", "free"],
)

# English: without criterion (10%)
register_oe(
    template_id="image_position.en.without_criterion.open_ended",
    introduction=["You are given one object placeholder in an image."],
    stem=["Where is [A] located in this image?"],
    question_instruction_profiles={"direct": EN_DIRECT, "sentence": EN_SENTENCE, "free": EMPTY_QUESTION_INSTRUCTION},
    answer_templates_by_type={
        "direct": ["[X_EN]"],
        "sentence": ["It is [X_EN]."],
        "free": ["It is [X_EN]."],
    },
    enabled_instruction_types=["direct", "sentence", "free"],
)
register_mcq(
    template_id="image_position.en.without_criterion.multiple_choice",
    introduction=["You are given one object placeholder in an image."],
    stem=["Choose where [A] is located in the image. Options: [OPTIONS_EN]"],
    question_instruction_profiles={"direct": EN_DIRECT, "sentence": EN_SENTENCE, "free": EMPTY_QUESTION_INSTRUCTION},
    answer_templates_by_type={
        "direct": ["[X_EN]"],
        "sentence": ["The correct option is [X_EN]."],
        "free": ["The correct option is [X_EN]."],
    },
    enabled_instruction_types=["direct", "sentence", "free"],
)

# Chinese: with criterion (90%)
register_oe(
    template_id="image_position.zh.with_criterion.open_ended",
    introduction=["你会看到图中的一个目标占位符。"],
    stem=["按九宫格判定准则（以 bbox 中心划分左右/中、上中下），[A] 位于图像的什么位置？"],
    question_instruction_profiles={"direct": ZH_DIRECT, "sentence": ZH_SENTENCE, "free": EMPTY_QUESTION_INSTRUCTION},
    answer_templates_by_type={
        "direct": ["[X_ZH]"],
        "sentence": ["它在[X_ZH]。"],
        "free": ["它在[X_ZH]。"],
    },
    enabled_instruction_types=["direct", "sentence", "free"],
)
register_mcq(
    template_id="image_position.zh.with_criterion.multiple_choice",
    introduction=["你会看到图中的一个目标占位符。"],
    stem=["按九宫格判定准则（以 bbox 中心划分左右/中、上中下），请选择 [A] 的位置。选项：[OPTIONS_ZH]"],
    question_instruction_profiles={"direct": ZH_DIRECT, "sentence": ZH_SENTENCE, "free": EMPTY_QUESTION_INSTRUCTION},
    answer_templates_by_type={
        "direct": ["[X_ZH]"],
        "sentence": ["正确选项是[X_ZH]。"],
        "free": ["正确选项是[X_ZH]。"],
    },
    enabled_instruction_types=["direct", "sentence", "free"],
)

# Chinese: without criterion (10%)
register_oe(
    template_id="image_position.zh.without_criterion.open_ended",
    introduction=["你会看到图中的一个目标占位符。"],
    stem=["[A] 在图像中的什么位置？"],
    question_instruction_profiles={"direct": ZH_DIRECT, "sentence": ZH_SENTENCE, "free": EMPTY_QUESTION_INSTRUCTION},
    answer_templates_by_type={
        "direct": ["[X_ZH]"],
        "sentence": ["它在[X_ZH]。"],
        "free": ["它在[X_ZH]。"],
    },
    enabled_instruction_types=["direct", "sentence", "free"],
)
register_mcq(
    template_id="image_position.zh.without_criterion.multiple_choice",
    introduction=["你会看到图中的一个目标占位符。"],
    stem=["请选择 [A] 在图像中的位置。选项：[OPTIONS_ZH]"],
    question_instruction_profiles={"direct": ZH_DIRECT, "sentence": ZH_SENTENCE, "free": EMPTY_QUESTION_INSTRUCTION},
    answer_templates_by_type={
        "direct": ["[X_ZH]"],
        "sentence": ["正确选项是[X_ZH]。"],
        "free": ["正确选项是[X_ZH]。"],
    },
    enabled_instruction_types=["direct", "sentence", "free"],
)
