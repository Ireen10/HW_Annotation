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


class BaseTask:
    """OpenSpatial-style base task: subclass and implement ``run``."""

    def __init__(self, *, stage_name: str, params: dict[str, Any]) -> None:
        self.stage_name = stage_name
        self.params = dict(params)

    def run(self, samples: tuple[AnnotationSample, ...]) -> TaskRunResult:
        raise NotImplementedError
