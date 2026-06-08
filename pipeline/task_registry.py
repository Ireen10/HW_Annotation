"""Task factory for stage kinds."""

from __future__ import annotations

from pipeline.base_task import BaseTask
from pipeline.qa import SpatialRelationQATask
from pipeline.tasks import RefineTask

TASK_REGISTRY: dict[str, type[BaseTask]] = {
    "refine": RefineTask,
    "qa": SpatialRelationQATask,
}


def create_task(kind: str, stage_name: str, params: dict) -> BaseTask:
    try:
        cls = TASK_REGISTRY[kind]
    except KeyError as exc:
        raise ValueError(f"unsupported stage kind: {kind!r}") from exc
    return cls(stage_name=stage_name, params=params)
