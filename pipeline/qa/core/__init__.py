"""Core contracts for metadata QA stage."""

from .mark_spec import MarkPlan, MarkSlot
from .prompt_template import PromptRenderRecord
from .question_type import QuestionType
from .sample_metadata import TurnMetadata
from .scene_graph import SceneGraph, SceneNode
from .spatial_rules import (
    ImagePlaneDirection,
    bbox_iou,
    closed_category_hit,
    directional_answer_from_tokens,
    has_orientation_relation,
    image_position_answer,
    image_position_consistent,
    infer_image_plane_direction,
    infer_manual_image_grid_key,
    normalized_center_distance,
    relation_tokens_between,
    relation_tokens_self,
)
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
    "ImagePlaneDirection",
    "bbox_iou",
    "normalized_center_distance",
    "infer_manual_image_grid_key",
    "image_position_answer",
    "image_position_consistent",
    "infer_image_plane_direction",
    "directional_answer_from_tokens",
    "has_orientation_relation",
    "closed_category_hit",
    "relation_tokens_between",
    "relation_tokens_self",
]
