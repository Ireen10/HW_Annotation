"""LLM prompt templates for refine."""

from __future__ import annotations

import json
from typing import Any


def reference_alignment_prompt(scene: dict[str, Any], issues: list[dict[str, Any]]) -> list[dict[str, str]]:
    system = (
        "You align spatial annotation references. Pick the correct reference object id per issue.\n"
        "Rules:\n"
        "1. Only use ids from the scene objects list.\n"
        "2. reference_label may be informal Chinese and not match object label exactly.\n"
        "3. If unsure, set reference_id to null and explain.\n"
        'Output JSON: {"alignments": [{"issue_id": str, "reference_id": str|null, "reason": str}]}'
    )
    user = json.dumps({"scene": scene, "issues": issues}, ensure_ascii=False, indent=2)
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def english_names_prompt(scene: dict[str, Any], object_ids: list[str]) -> list[dict[str, str]]:
    system = (
        "Provide concise English object names for annotation labels (noun phrases, not sentences).\n"
        "Rules:\n"
        "1. name_en: 1-6 English words, lowercase except proper nouns.\n"
        "2. Keep distinct objects distinguishable (e.g. front bed vs back bed).\n"
        'Output JSON: {"names": [{"object_id": str, "name_en": str, "reason": str}]}'
    )
    user = json.dumps({"scene": scene, "object_ids": object_ids}, ensure_ascii=False, indent=2)
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def closed_category_prompt(
    scene: dict[str, Any],
    object_ids: list[str],
    allowed_categories: list[str],
) -> list[dict[str, str]]:
    system = (
        "Classify objects that have orientation into ONE closed-set English category.\n"
        "Rules:\n"
        "1. category_en must be exactly one value from allowed_categories.\n"
        "2. Use 'other' when unsure.\n"
        'Output JSON: {"categories": [{"object_id": str, "category_en": str, "reason": str}]}'
    )
    user = json.dumps(
        {"scene": scene, "object_ids": object_ids, "allowed_categories": allowed_categories},
        ensure_ascii=False,
        indent=2,
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def open_category_prompt(scene: dict[str, Any], object_ids: list[str]) -> list[dict[str, str]]:
    system = (
        "Assign open-set English category labels (noun phrases: bed, pillow, lamp, magazine).\n"
        "Rules:\n"
        "1. category_en: 1-4 English words.\n"
        'Output JSON: {"categories": [{"object_id": str, "category_en": str, "reason": str}]}'
    )
    user = json.dumps({"scene": scene, "object_ids": object_ids}, ensure_ascii=False, indent=2)
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def positional_tags_prompt(scene: dict[str, Any], relations: list[dict[str, Any]]) -> list[dict[str, str]]:
    system = (
        "Map each relation's raw positional_relationship to canonical English positional_tags.\n"
        "Tags are vocabulary labels for training/QA, NOT free-form text.\n"
        "Rules:\n"
        "1. topology: only in, on, surround\n"
        "2. image-based: only up, down, left, right, middle\n"
        "3. egocentric/orientation/allocentric: up, down, left, right, in_front_of, behind\n"
        "4. Output one tag list per issue_id; may be multi-tag.\n"
        'Output JSON: {"tags": [{"issue_id": str, "positional_tags": [str], "reason": str}]}'
    )
    user = json.dumps({"scene": scene, "relations": relations}, ensure_ascii=False, indent=2)
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]
