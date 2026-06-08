"""Scaffold QA task for spatial-relation families."""

from __future__ import annotations

from pipeline.qa.base_qa_task import BaseQATask


class SpatialRelationQATask(BaseQATask):
    SUB_TASKS = (
        "scene_caption",
        "image_position",
        "image_relative_position",
        "object_orientation",
        "egocentric_reltaion",
        "allocentric_relation",
    )
