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
        "Classify orientation-participant objects into ONE closed-set English category.\n"
        "Rules:\n"
        "1. category_en must be exactly one value from allowed_categories.\n"
        "2. Use 'other' when unsure.\n"
        "3. category_en is a label token for downstream logic, not free-form text.\n"
        "4. Perspective criteria:\n"
        "   - person / animal / humanoid_doll: viewpoint-substitutable entities.\n"
        "   - vehicle: include car, bicycle, bus, train, airplane, ship; heading/viewpoint can be substituted.\n"
        "   - chair_with_backrest / sofa_with_backrest / bed / desk / screen: use-scenario-substitutable objects;\n"
        "     orientation inferred by typical use direction (e.g., facing screen, facing desk side, bed head direction).\n"
        "5. Prefer specific class over 'other' when evidence is sufficient.\n"
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


def unified_refine_prompt(
    scene: dict[str, Any],
    object_tasks: list[dict[str, Any]],
    relation_tasks: list[dict[str, Any]],
    allowed_closed_categories: list[str],
    closed_fallback_label: str,
) -> list[dict[str, str]]:
    system = (
        "You refine one spatial-annotation sample in ONE pass.\n"
        "Return names, categories, reference_id fixes, and positional_tags in a single JSON object.\n"
        "Hard rules:\n"
        "1. object_id/reference_id must come from scene.objects ids only.\n"
        "2. For participates_in_orientation=true:\n"
        "   - closed_category_en must be one of allowed_closed_categories.\n"
        "   - if uncertain, use closed_fallback_label.\n"
        "   - category_en should be the final label (open-set fallback if closed_category_en is fallback).\n"
        "3. For open-ended category targets (object_tasks.requires_open_category=true),\n"
        "   category_en MUST be a specific open-ended English noun phrase (e.g. nightstand, floor lamp),\n"
        "   and MUST NOT equal closed_fallback_label.\n"
        "4. positional_tags must follow relationship_type vocabulary:\n"
        "   - topology: in|on|surround\n"
        "   - image-based: up|down|left|right|middle\n"
        "   - egocentric/orientation/allocentric: up|down|left|right|in_front_of|behind\n"
        "5. If reference cannot be resolved confidently, keep reference_id as null.\n"
        "Output JSON schema:\n"
        '{'
        '"objects":[{"object_id":str,"name_en":str,"category_en":str,'
        '"closed_category_en":str|null,"reason":str}],'
        '"relations":[{"issue_id":str,"reference_id":str|null,'
        '"positional_tags":[str],"reason":str}]'
        "}"
    )
    user = json.dumps(
        {
            "scene": scene,
            "object_tasks": object_tasks,
            "relation_tasks": relation_tasks,
            "allowed_closed_categories": allowed_closed_categories,
            "closed_fallback_label": closed_fallback_label,
        },
        ensure_ascii=False,
        indent=2,
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]
