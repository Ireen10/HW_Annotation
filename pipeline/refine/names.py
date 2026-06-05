"""English object names via LLM."""

from __future__ import annotations

from typing import TYPE_CHECKING

from hw_annotation.parse.sample import AnnotatedObject, AnnotationSample, replace_object

if TYPE_CHECKING:
    from pipeline.utils.llm import OpenAICompatibleClient


def assign_english_names(
    sample: AnnotationSample,
    objects: tuple[AnnotatedObject, ...],
    client: OpenAICompatibleClient,
) -> tuple[tuple[AnnotatedObject, ...], list[str]]:
    from .prompts import english_names_prompt

    ids = [o.id for o in objects]
    scene = {
        "item_id": sample.item_id,
        "scenario": sample.scenario,
        "objects": [{"id": o.id, "label": o.label} for o in objects],
    }
    messages = english_names_prompt(scene, ids)
    raw = client.chat(messages, json_mode=True)
    payload = client.parse_json_content(raw)
    by_id = {
        row["object_id"]: row
        for row in (payload.get("names") or [])
        if row.get("object_id")
    }

    notes: list[str] = []
    updated: list[AnnotatedObject] = []
    for obj in objects:
        row = by_id.get(obj.id, {})
        name_en = (row.get("name_en") or "").strip() or None
        if not name_en:
            notes.append(f"{obj.id}: missing name_en from LLM")
        updated.append(replace_object(obj, name_en=name_en))
    return tuple(updated), notes
