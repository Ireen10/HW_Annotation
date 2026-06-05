"""Map raw positional values to validated English positional_tags."""

from __future__ import annotations

from typing import TYPE_CHECKING

from hw_annotation.parse.sample import AnnotatedObject, AnnotationSample, replace_object, replace_relation
from hw_annotation.vocab.constants import (
    DIRECTIONAL_3D_VALUES,
    IMAGE_BASED_VALUES,
    TOPOLOGY_VALUES,
)

if TYPE_CHECKING:
    from pipeline.utils.llm import OpenAICompatibleClient


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


def relations_needing_tag_llm(objects: tuple[AnnotatedObject, ...]) -> list[dict]:
    pending: list[dict] = []
    for obj in objects:
        for idx, rel in enumerate(obj.relations):
            if rel.positional_tags:
                continue
            pending.append(
                {
                    "issue_id": f"{obj.id}:{idx}",
                    "object_id": obj.id,
                    "rel_index": idx,
                    "relationship_type": rel.relationship_type,
                    "positional_relationship": list(rel.positional_relationship),
                }
            )
    return pending


def apply_tag_llm_results(
    objects: tuple[AnnotatedObject, ...],
    tag_rows: list[dict],
) -> tuple[AnnotatedObject, ...]:
    by_issue = {r.get("issue_id"): r for r in tag_rows}
    out: list[AnnotatedObject] = []
    for obj in objects:
        new_rels = []
        for idx, rel in enumerate(obj.relations):
            issue_id = f"{obj.id}:{idx}"
            row = by_issue.get(issue_id)
            if row and row.get("positional_tags"):
                tags = tuple(row["positional_tags"])
                new_rels.append(replace_relation(rel, positional_tags=tags))
            else:
                new_rels.append(rel)
        out.append(replace_object(obj, relations=tuple(new_rels)))
    return tuple(out)


def assign_positional_tags_llm(
    sample: AnnotationSample,
    objects: tuple[AnnotatedObject, ...],
    client: OpenAICompatibleClient,
) -> tuple[tuple[AnnotatedObject, ...], list[str]]:
    from .prompts import positional_tags_prompt

    pending = relations_needing_tag_llm(objects)
    if not pending:
        return objects, []

    scene = {
        "item_id": sample.item_id,
        "scenario": sample.scenario,
        "allowed_topology": sorted(TOPOLOGY_VALUES),
        "allowed_image_based": sorted(IMAGE_BASED_VALUES),
        "allowed_directional_3d": sorted(DIRECTIONAL_3D_VALUES),
    }
    messages = positional_tags_prompt(scene, pending)
    raw = client.chat(messages, json_mode=True)
    payload = client.parse_json_content(raw)
    rows = payload.get("tags") or []
    return apply_tag_llm_results(objects, rows), []
