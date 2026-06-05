"""Validate :class:`AnnotationSample` after refine (vocabulary + required fields)."""

from __future__ import annotations

from .sample import AnnotatedObject, AnnotationSample, SpatialRelation
from ..vocab.constants import (
    DIRECTIONAL_3D_VALUES,
    IMAGE_BASED_VALUES,
    RELATIONSHIP_TYPES,
    TOPOLOGY_VALUES,
)


def _allowed_tags_for_rel_type(rel_type: str) -> frozenset[str]:
    if rel_type == "topology":
        return TOPOLOGY_VALUES
    if rel_type == "image-based":
        return IMAGE_BASED_VALUES
    return DIRECTIONAL_3D_VALUES


def validate_relation(rel: SpatialRelation, *, prefix: str) -> list[str]:
    errors: list[str] = []
    if rel.relationship_type not in RELATIONSHIP_TYPES:
        errors.append(f"{prefix}: unknown relationship_type {rel.relationship_type!r}")
        return errors

    if rel.positional_relationship and not rel.positional_tags:
        errors.append(f"{prefix}: missing positional_tags for non-empty positional_relationship")
    if not rel.positional_relationship and not rel.positional_tags:
        return errors
    if not rel.positional_tags:
        errors.append(f"{prefix}: positional_tags must be set after refine")
        return errors

    allowed = _allowed_tags_for_rel_type(rel.relationship_type)
    unknown = [t for t in rel.positional_tags if t not in allowed]
    if unknown:
        errors.append(f"{prefix}: positional_tags {unknown} not in allowed set for {rel.relationship_type}")

    if rel.reference_label and not rel.reference_id:
        errors.append(f"{prefix}: reference_label set but reference_id is missing")
    if rel.reference_ambiguous:
        errors.append(f"{prefix}: reference_ambiguous is true after refine")
    return errors


def validate_object(obj: AnnotatedObject, *, prefix: str) -> list[str]:
    errors: list[str] = []
    if not (obj.name_en or "").strip():
        errors.append(f"{prefix}: missing name_en")
    if not (obj.category_en or "").strip():
        errors.append(f"{prefix}: missing category_en")
    for i, rel in enumerate(obj.relations):
        errors.extend(validate_relation(rel, prefix=f"{prefix}.relations[{i}]"))
    return errors


def validate_refined_sample(sample: AnnotationSample) -> list[str]:
    """
    Validate a refined sample. Raw loader samples (``is_refined=False``) are not checked here.
    """
    if not sample.is_refined:
        return ["sample is not marked refined (is_refined=False)"]

    errors: list[str] = []
    if not sample.objects:
        errors.append("objects: must be non-empty")
    for i, obj in enumerate(sample.objects):
        errors.extend(validate_object(obj, prefix=f"objects[{i}]"))

    ids = {o.id for o in sample.objects}
    for i, obj in enumerate(sample.objects):
        for j, rel in enumerate(obj.relations):
            if rel.reference_id and rel.reference_id not in ids:
                errors.append(
                    f"objects[{i}].relations[{j}]: reference_id not in sample objects"
                )
    return errors
