"""Scene graph contracts for QA stage."""

from __future__ import annotations

from dataclasses import dataclass

from hw_annotation import AnnotationSample


@dataclass(frozen=True, slots=True)
class SceneNode:
    object_id: str
    object_label: str
    bbox_xyxy: tuple[float, float, float, float]


@dataclass(frozen=True, slots=True)
class SceneGraph:
    item_id: str
    image_ref: str
    nodes: tuple[SceneNode, ...]

    @classmethod
    def from_sample(cls, sample: AnnotationSample) -> SceneGraph:
        return cls(
            item_id=sample.item_id,
            image_ref=sample.image.file_path,
            nodes=tuple(
                SceneNode(
                    object_id=obj.id,
                    object_label=obj.label,
                    bbox_xyxy=obj.bbox_xyxy,
                )
                for obj in sample.objects
            ),
        )
