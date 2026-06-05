"""LLM prompt templates for refine."""

from __future__ import annotations

import json
from typing import Any


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
