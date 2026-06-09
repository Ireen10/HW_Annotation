"""Scene graph contracts for QA stage."""

from __future__ import annotations

from dataclasses import dataclass

from hw_annotation import AnnotationSample, SpatialRelation


@dataclass(frozen=True, slots=True)
class SceneNode:
    object_id: str
    object_label: str
    bbox_xyxy: tuple[float, float, float, float]
    relations: tuple[SpatialRelation, ...]
    name_en: str | None = None
    category_en: str | None = None
    closed_category_en: str | None = None
    closed_category_hit: bool | None = None

    def display_name(self, lang: str) -> str:
        if lang == "zh":
            return self.object_label
        return (self.name_en or "").strip() or self.object_label


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
                    relations=obj.relations,
                    name_en=obj.name_en,
                    category_en=obj.category_en,
                    closed_category_en=obj.closed_category_en,
                    closed_category_hit=obj.closed_category_hit,
                )
                for obj in sample.objects
            ),
        )

    def get_node(self, object_id: str) -> SceneNode | None:
        for node in self.nodes:
            if node.object_id == object_id:
                return node
        return None
