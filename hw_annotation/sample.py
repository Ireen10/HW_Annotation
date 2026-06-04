"""Lean per-image sample: scene + objects + spatial relations (no platform/UI noise)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .normalize import parse_annotation_payload


@dataclass(frozen=True, slots=True)
class SpatialRelation:
    relationship_type: str
    positional_relationship: tuple[str, ...]
    reference_label: str | None = None
    reference_id: str | None = None
    reference_ambiguous: bool = False

    @classmethod
    def from_parsed(cls, raw: dict[str, Any]) -> SpatialRelation:
        return cls(
            relationship_type=raw["relationship_type"],
            positional_relationship=tuple(raw["positional_relationship"]),
            reference_label=raw.get("reference_label"),
            reference_id=raw.get("reference_id"),
            reference_ambiguous=bool(raw.get("reference_ambiguous")),
        )


@dataclass(frozen=True, slots=True)
class AnnotatedObject:
    id: str
    label: str
    bbox_xyxy: tuple[float, float, float, float]
    relations: tuple[SpatialRelation, ...] = ()

    @classmethod
    def from_parsed(cls, raw: dict[str, Any]) -> AnnotatedObject:
        bbox = raw["bbox_xyxy"]
        return cls(
            id=raw["id"],
            label=raw["label"],
            bbox_xyxy=(float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])),
            relations=tuple(SpatialRelation.from_parsed(r) for r in raw.get("relations") or []),
        )


@dataclass(frozen=True, slots=True)
class ImageRef:
    url: str
    file_path: str


@dataclass(frozen=True, slots=True)
class AnnotationSample:
    """One merged image annotation ready for downstream metadata/QA builders."""

    item_id: str
    batch: str
    image: ImageRef
    scenario: str
    objects: tuple[AnnotatedObject, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "item_id": self.item_id,
            "batch": self.batch,
            "image": {"url": self.image.url, "file_path": self.image.file_path},
            "scenario": self.scenario,
        }
        d["objects"] = [
            {
                "id": o.id,
                "label": o.label,
                "bbox_xyxy": list(o.bbox_xyxy),
                "relations": [
                    {
                        "relationship_type": r.relationship_type,
                        "positional_relationship": list(r.positional_relationship),
                        "reference_label": r.reference_label,
                        "reference_id": r.reference_id,
                        "reference_ambiguous": r.reference_ambiguous,
                    }
                    for r in o.relations
                ],
            }
            for o in self.objects
        ]
        return d

    @property
    def object_count(self) -> int:
        return len(self.objects)

    @property
    def relation_count(self) -> int:
        return sum(len(o.relations) for o in self.objects)


def parse_sample(record: dict[str, Any]) -> AnnotationSample:
    """Parse one raw JSONL export row into a lean :class:`AnnotationSample`."""
    ann = parse_annotation_payload(record["_annotation"])
    return AnnotationSample(
        item_id=record["item_id"],
        batch=record["batch"],
        image=ImageRef(url=record["url"], file_path=record["filePath"]),
        scenario=ann["scenario"],
        objects=tuple(AnnotatedObject.from_parsed(o) for o in ann["objects"]),
    )
