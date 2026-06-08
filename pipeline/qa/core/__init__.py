"""Core contracts for metadata QA stage."""

from .mark_spec import MarkPlan, MarkSlot
from .prompt_template import PromptRenderRecord
from .question_type import QuestionType
from .sample_metadata import TurnMetadata
from .scene_graph import SceneGraph, SceneNode
from .structured_prompt_template import (
    AnswerInstructionProfile,
    STRUCTURED_TEMPLATE_REGISTRY,
    StructuredPromptTemplate,
    StructuredTemplateRegistry,
)

__all__ = [
    "QuestionType",
    "PromptRenderRecord",
    "StructuredPromptTemplate",
    "AnswerInstructionProfile",
    "StructuredTemplateRegistry",
    "STRUCTURED_TEMPLATE_REGISTRY",
    "SceneGraph",
    "SceneNode",
    "MarkPlan",
    "MarkSlot",
    "TurnMetadata",
]
