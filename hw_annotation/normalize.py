"""Parse platform ``_annotation`` JSON into a lean, UI-free structure."""

from __future__ import annotations

import json
from typing import Any

from .constants import (
    DIRECTIONAL_3D_VALUES,
    IMAGE_BASED_VALUES,
    RELATIONSHIP_TYPES,
    TOPOLOGY_VALUES,
)


def _bbox_from_rectangle_points(points: list[dict[str, float]]) -> list[float]:
    xs = [p["x"] for p in points]
    ys = [p["y"] for p in points]
    return [min(xs), min(ys), max(xs), max(ys)]


def _normalize_relation(raw: dict[str, Any]) -> dict[str, Any]:
    rel_type = raw.get("relationship_type", "")
    if rel_type not in RELATIONSHIP_TYPES:
        raise ValueError(f"unknown relationship_type: {rel_type!r}")

    positional = list(raw.get("positional_relationship") or [])
    ref_label = (raw.get("reference_object") or "").strip() or None

    _validate_positional(rel_type, positional)

    return {
        "relationship_type": rel_type,
        "positional_relationship": positional,
        "reference_label": ref_label,
        "reference_id": None,
        "reference_ambiguous": False,
    }


def _validate_positional(rel_type: str, positional: list[str]) -> None:
    if not positional:
        raise ValueError(f"{rel_type}: positional_relationship must be non-empty")
    allowed: frozenset[str]
    if rel_type == "topology":
        allowed = TOPOLOGY_VALUES
    elif rel_type == "image-based":
        allowed = IMAGE_BASED_VALUES
    else:
        allowed = DIRECTIONAL_3D_VALUES
    unknown = [p for p in positional if p not in allowed]
    if unknown:
        raise ValueError(f"{rel_type}: unknown positional values {unknown}")


def _resolve_reference_ids(objects: list[dict[str, Any]]) -> None:
    by_label: dict[str, list[str]] = {}
    for obj in objects:
        by_label.setdefault(obj["label"], []).append(obj["id"])

    for obj in objects:
        for rel in obj["relations"]:
            label = rel.get("reference_label")
            if not label:
                continue
            candidates = by_label.get(label, [])
            if len(candidates) == 1:
                rel["reference_id"] = candidates[0]
            elif len(candidates) > 1:
                rel["reference_id"] = candidates[0]
                rel["reference_ambiguous"] = True


def parse_annotation_payload(raw_annotation: str | dict[str, Any]) -> dict[str, Any]:
    """
    Parse ``_annotation`` (string or dict).

    Strips UI-only fragment fields (color, selected, points, rotateDegree, …).
    """
    if isinstance(raw_annotation, str):
        payload = json.loads(raw_annotation)
    else:
        payload = raw_annotation

    objects: list[dict[str, Any]] = []
    for frag in payload.get("image-fragments") or []:
        points = frag.get("points") or []
        if not points:
            raise ValueError(f"fragment {frag.get('id')}: missing points for bbox")
        relations = [_normalize_relation(a) for a in (frag.get("attrs") or [])]
        objects.append(
            {
                "id": frag["id"],
                "label": (frag.get("objectLabel") or "").strip(),
                "bbox_xyxy": _bbox_from_rectangle_points(points),
                "relations": relations,
            }
        )

    _resolve_reference_ids(objects)
    return {
        "scenario": (payload.get("scenario") or "").strip(),
        "objects": objects,
    }
