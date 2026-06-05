"""English category assignment after reference alignment."""

from __future__ import annotations

from typing import TYPE_CHECKING

from hw_annotation.parse.sample import AnnotatedObject, AnnotationSample, replace_object
from pipeline.config import RefineConfig

if TYPE_CHECKING:
    from pipeline.utils.llm import OpenAICompatibleClient


def assign_categories(
    sample: AnnotationSample,
    objects: tuple[AnnotatedObject, ...],
    client: OpenAICompatibleClient,
    config: RefineConfig,
) -> tuple[tuple[AnnotatedObject, ...], list[str]]:
    notes: list[str] = []
    allowed = list(config.orientation_closed_categories)
    fallback = config.closed_fallback_label

    orient_ids = [o.id for o in objects if o.participates_in_orientation]
    general_ids = [o.id for o in objects if not o.participates_in_orientation]

    closed_map: dict[str, dict] = {}
    if orient_ids:
        closed_map = _fetch_closed_categories(sample, objects, orient_ids, allowed, client)

    open_targets = list(general_ids)
    for oid in orient_ids:
        entry = closed_map.get(oid, {})
        cat = (entry.get("category_en") or "").strip()
        if not cat or cat == fallback or cat not in allowed:
            open_targets.append(oid)

    open_map: dict[str, dict] = {}
    if open_targets:
        open_map = _fetch_open_categories(sample, objects, open_targets, client)

    updated: list[AnnotatedObject] = []
    for obj in objects:
        if obj.id in orient_ids:
            entry = closed_map.get(obj.id, {})
            closed_cat = (entry.get("category_en") or "").strip() or None
            hit = closed_cat is not None and closed_cat in allowed and closed_cat != fallback
            if hit:
                updated.append(
                    _with_category(
                        obj,
                        category_en=closed_cat,
                        category_source="closed",
                        closed_category_en=closed_cat,
                        closed_category_hit=True,
                    )
                )
                continue
            open_entry = open_map.get(obj.id, {})
            open_cat = (open_entry.get("category_en") or "").strip() or None
            if not closed_cat:
                notes.append(f"{obj.id}: closed-set category missing; used open-set")
            else:
                notes.append(f"{obj.id}: closed-set '{closed_cat}' → open-set fallback")
            updated.append(
                _with_category(
                    obj,
                    category_en=open_cat,
                    category_source="open",
                    closed_category_en=closed_cat,
                    closed_category_hit=False,
                )
            )
        else:
            open_entry = open_map.get(obj.id, {})
            open_cat = (open_entry.get("category_en") or "").strip() or None
            updated.append(
                _with_category(
                    obj,
                    category_en=open_cat,
                    category_source="open",
                    closed_category_en=None,
                    closed_category_hit=None,
                )
            )

    return tuple(updated), notes


def _with_category(obj: AnnotatedObject, **kwargs) -> AnnotatedObject:
    return replace_object(obj, **kwargs)


def _fetch_closed_categories(
    sample: AnnotationSample,
    objects: tuple[AnnotatedObject, ...],
    object_ids: list[str],
    allowed: list[str],
    client: OpenAICompatibleClient,
) -> dict[str, dict]:
    from .prompts import closed_category_prompt

    scene = {
        "item_id": sample.item_id,
        "scenario": sample.scenario,
        "objects": [{"id": o.id, "label": o.label, "name_en": o.name_en} for o in objects],
    }
    messages = closed_category_prompt(scene, object_ids, allowed)
    raw = client.chat(messages, json_mode=True)
    payload = client.parse_json_content(raw)
    return {
        row["object_id"]: row
        for row in (payload.get("categories") or [])
        if row.get("object_id")
    }


def _fetch_open_categories(
    sample: AnnotationSample,
    objects: tuple[AnnotatedObject, ...],
    object_ids: list[str],
    client: OpenAICompatibleClient,
) -> dict[str, dict]:
    from .prompts import open_category_prompt

    scene = {
        "item_id": sample.item_id,
        "scenario": sample.scenario,
        "objects": [{"id": o.id, "label": o.label, "name_en": o.name_en} for o in objects],
    }
    messages = open_category_prompt(scene, object_ids)
    raw = client.chat(messages, json_mode=True)
    payload = client.parse_json_content(raw)
    return {
        row["object_id"]: row
        for row in (payload.get("categories") or [])
        if row.get("object_id")
    }
