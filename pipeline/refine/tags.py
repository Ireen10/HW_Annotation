"""Map raw positional values to validated English positional_tags."""

from __future__ import annotations

from hw_annotation.parse.sample import AnnotatedObject, replace_object, replace_relation
from hw_annotation.vocab.constants import (
    DIRECTIONAL_3D_VALUES,
    IMAGE_BASED_VALUES,
    TOPOLOGY_VALUES,
)


def _allowed_for_type(rel_type: str) -> frozenset[str]:
    if rel_type == "topology":
        return TOPOLOGY_VALUES
    if rel_type == "image-based":
        return IMAGE_BASED_VALUES
    return DIRECTIONAL_3D_VALUES


def infer_positional_tags(rel_type: str, positional: tuple[str, ...]) -> tuple[str, ...] | None:
    """Return tags if every raw token is already a valid English tag; else None."""
    if not positional:
        return ()
    allowed = _allowed_for_type(rel_type)
    if all(p in allowed for p in positional):
        return positional
    return None


def apply_positional_tags_rule(objects: tuple[AnnotatedObject, ...]) -> tuple[AnnotatedObject, ...]:
    updated: list[AnnotatedObject] = []
    for obj in objects:
        new_rels = []
        for rel in obj.relations:
            tags = infer_positional_tags(rel.relationship_type, rel.positional_relationship)
            if tags is not None:
                new_rels.append(replace_relation(rel, positional_tags=tags))
            else:
                new_rels.append(rel)
        updated.append(replace_object(obj, relations=tuple(new_rels)))
    return tuple(updated)
