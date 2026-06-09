"""Base task abstraction for pipeline stages."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from hw_annotation import AnnotationSample


@dataclass(frozen=True, slots=True)
class TaskRunResult:
    samples: tuple[AnnotationSample, ...]
    failed_count: int = 0
    notes: tuple[str, ...] = field(default_factory=tuple)
    artifacts: dict[str, object] = field(default_factory=dict)
    wrote_main_output: bool = False


class BaseTask:
    """OpenSpatial-style base task: subclass and implement ``run``."""
    incremental_resume_capable: bool = False

    def __init__(self, *, stage_name: str, params: dict[str, Any]) -> None:
        self.stage_name = stage_name
        self.params = dict(params)
        self.runtime_context: dict[str, Any] = {}

    def set_runtime_context(self, **kwargs: Any) -> None:
        self.runtime_context = dict(kwargs)

    def run(self, samples: tuple[AnnotationSample, ...]) -> TaskRunResult:
        raise NotImplementedError
