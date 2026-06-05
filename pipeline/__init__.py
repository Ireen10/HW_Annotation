"""Annotation pipeline: refine → metadata → QA (downstream)."""

from .config import (
    DEFAULT_ORIENTATION_CLOSED_CATEGORIES,
    LLMSettings,
    RefineConfig,
)
from .runtime import (
    PipelineResult,
    PipelineSpec,
    StageResult,
    StageSpec,
    build_default_pipeline_spec,
    load_pipeline_spec,
    run_pipeline,
)
from .refine import export_samples_jsonl, refine_dataset, refine_iter, refine_sample
from .utils import LLMError, OpenAICompatibleClient

__all__ = [
    "RefineConfig",
    "LLMSettings",
    "DEFAULT_ORIENTATION_CLOSED_CATEGORIES",
    "LLMError",
    "OpenAICompatibleClient",
    "StageSpec",
    "PipelineSpec",
    "StageResult",
    "PipelineResult",
    "load_pipeline_spec",
    "build_default_pipeline_spec",
    "run_pipeline",
    "refine_sample",
    "refine_dataset",
    "refine_iter",
    "export_samples_jsonl",
]
