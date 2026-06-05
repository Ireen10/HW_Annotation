"""Per-image annotation sample (raw load + refined downstream fields on same types)."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from .normalize import parse_annotation_payload
from .types import CategorySource, ReferenceAlignment


@dataclass(frozen=True, slots=True)
class SpatialRelation:
    """Spatial relation on an object. ``positional_tags`` are canonical English labels after refine."""

    relationship_type: str
    positional_relationship: tuple[str, ...]
    positional_tags: tuple[str, ...] = ()
    reference_label: str | None = None
    reference_id: str | None = None
    reference_ambiguous: bool = False
    reference_alignment: ReferenceAlignment = "none"
    alignment_note: str | None = None

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
    name_en: str | None = None
    category_en: str | None = None
    participates_in_orientation: bool = False
    category_source: CategorySource = "none"
    closed_category_en: str | None = None
    closed_category_hit: bool | None = None

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
    """
    One image annotation.

    Loader fills core geometry/relations faithfully (Chinese ``label``, raw ``positional_relationship``).
    Refine enriches the same record with English names/categories/tags and runs validation.
    """

    item_id: str
    batch: str
    image: ImageRef
    scenario: str
    objects: tuple[AnnotatedObject, ...] = field(default_factory=tuple)
    is_refined: bool = False
    refine_notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "item_id": self.item_id,
            "batch": self.batch,
            "image": {"url": self.image.url, "file_path": self.image.file_path},
            "scenario": self.scenario,
            "is_refined": self.is_refined,
            "refine_notes": list(self.refine_notes),
        }
        d["objects"] = [
            {
                "id": o.id,
                "label": o.label,
                "name_en": o.name_en,
                "category_en": o.category_en,
                "bbox_xyxy": list(o.bbox_xyxy),
                "participates_in_orientation": o.participates_in_orientation,
                "category_source": o.category_source,
                "closed_category_en": o.closed_category_en,
                "closed_category_hit": o.closed_category_hit,
                "relations": [
                    {
                        "relationship_type": r.relationship_type,
                        "positional_relationship": list(r.positional_relationship),
                        "positional_tags": list(r.positional_tags),
                        "reference_label": r.reference_label,
                        "reference_id": r.reference_id,
                        "reference_ambiguous": r.reference_ambiguous,
                        "reference_alignment": r.reference_alignment,
                        "alignment_note": r.alignment_note,
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

    def with_updates(
        self,
        *,
        objects: tuple[AnnotatedObject, ...] | None = None,
        is_refined: bool | None = None,
        refine_notes: tuple[str, ...] | None = None,
    ) -> AnnotationSample:
        kwargs: dict[str, Any] = {}
        if objects is not None:
            kwargs["objects"] = objects
        if is_refined is not None:
            kwargs["is_refined"] = is_refined
        if refine_notes is not None:
            kwargs["refine_notes"] = refine_notes
        return replace(self, **kwargs)


def parse_sample(record: dict[str, Any]) -> AnnotationSample:
    """Parse one raw JSONL export row (unrefined, no vocabulary validation)."""
    ann = parse_annotation_payload(record["_annotation"])
    return AnnotationSample(
        item_id=record["item_id"],
        batch=record["batch"],
        image=ImageRef(url=record["url"], file_path=record["filePath"]),
        scenario=ann["scenario"],
        objects=tuple(AnnotatedObject.from_parsed(o) for o in ann["objects"]),
        is_refined=False,
    )


def replace_object(obj: AnnotatedObject, **changes: Any) -> AnnotatedObject:
    return replace(obj, **changes)


def replace_relation(rel: SpatialRelation, **changes: Any) -> SpatialRelation:
    return replace(rel, **changes)
