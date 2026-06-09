"""Lightweight mark overlay helpers for QA visualization."""

from __future__ import annotations

from PIL import Image, ImageDraw

_SLOT_COLORS = {
    "A": (255, 87, 34),
    "B": (33, 150, 243),
    "C": (76, 175, 80),
    "D": (156, 39, 176),
}


def pil_to_base64(img: Image.Image) -> str:
    import base64
    import io

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def _slot_color(slot_id: str) -> tuple[int, int, int]:
    return _SLOT_COLORS.get(slot_id.upper(), (244, 67, 54))


def apply_marks_to_image(
    image: Image.Image,
    mark_spec: dict,
    slot_ids: list[str] | None,
    bbox_lookup: dict[str, tuple[float, float, float, float]] | None = None,
) -> Image.Image:
    frame = image.copy()
    draw = ImageDraw.Draw(frame)
    slots = mark_spec.get("slots") or []
    if not isinstance(slots, list):
        return frame

    selected = {s.upper() for s in (slot_ids or [])}
    width, height = frame.size

    for slot in slots:
        if not isinstance(slot, dict):
            continue
        slot_id = str(slot.get("slot_id") or "")
        if selected and slot_id.upper() not in selected:
            continue

        geometry = slot.get("geometry") or {}
        bbox = None
        if isinstance(geometry, dict) and geometry.get("bbox_xyxy"):
            raw = geometry["bbox_xyxy"]
            if isinstance(raw, (list, tuple)) and len(raw) == 4:
                bbox = tuple(float(v) for v in raw)
        if bbox is None and bbox_lookup:
            bbox = bbox_lookup.get(str(slot.get("object_id") or ""))

        color = _slot_color(slot_id)
        label = str(slot.get("object_label") or slot_id)

        if bbox is not None:
            x1, y1, x2, y2 = _bbox_to_pixels(bbox, width, height)
            draw.rectangle([x1, y1, x2, y2], outline=color, width=3)
            draw.text((x1 + 4, max(0, y1 - 16)), f"{slot_id}:{label}", fill=color)
        else:
            draw.text((8, 8 + 18 * (ord(slot_id[:1]) % 8)), f"{slot_id}:{label}", fill=color)

    return frame


def _bbox_to_pixels(
    bbox_xyxy: tuple[float, float, float, float],
    width: int,
    height: int,
) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = bbox_xyxy
    if max(x1, y1, x2, y2) <= 1.05 and min(x1, y1) >= -0.05:
        return (
            int(x1 * width),
            int(y1 * height),
            int(x2 * width),
            int(y2 * height),
        )
    return int(x1), int(y1), int(x2), int(y2)


def load_bbox_lookup_from_refined_jsonl(path: str) -> dict[str, dict[str, tuple[float, float, float, float]]]:
    """item_id -> {object_id: bbox_xyxy}"""
    lookup: dict[str, dict[str, tuple[float, float, float, float]]] = {}
    from pipeline.export.upstream_read import read_jsonl_records

    for row in read_jsonl_records(path):
        item_id = str(row.get("item_id") or "")
        if not item_id:
            continue
        obj_map: dict[str, tuple[float, float, float, float]] = {}
        for obj in row.get("objects") or []:
            if not isinstance(obj, dict):
                continue
            oid = str(obj.get("id") or "")
            bbox = obj.get("bbox_xyxy")
            if oid and isinstance(bbox, (list, tuple)) and len(bbox) == 4:
                obj_map[oid] = tuple(float(v) for v in bbox)
        if obj_map:
            lookup[item_id] = obj_map
    return lookup
