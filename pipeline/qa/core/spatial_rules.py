"""Geometry and relation utilities for spatial QA tasks."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .scene_graph import SceneGraph, SceneNode

IMAGE_BASED_TOKENS = {"left", "right", "up", "down", "middle"}
ZH_DIRECTION = {
    "left": "左边",
    "right": "右边",
    "up": "上方",
    "down": "下方",
    "middle": "中间",
    "up_left": "左上方",
    "up_right": "右上方",
    "down_left": "左下方",
    "down_right": "右下方",
}
EN_DIRECTION = {
    "left": "left",
    "right": "right",
    "up": "above",
    "down": "below",
    "middle": "middle",
    "up_left": "upper-left",
    "up_right": "upper-right",
    "down_left": "lower-left",
    "down_right": "lower-right",
}


@dataclass(frozen=True, slots=True)
class ImagePlaneDirection:
    key: str
    en_label: str
    zh_label: str


def bbox_center(bbox_xyxy: tuple[float, float, float, float]) -> tuple[float, float]:
    x1, y1, x2, y2 = bbox_xyxy
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


def bbox_iou(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)
    iw = max(0.0, inter_x2 - inter_x1)
    ih = max(0.0, inter_y2 - inter_y1)
    inter = iw * ih
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter
    if union <= 0:
        return 0.0
    return inter / union


def normalized_center_distance(graph: SceneGraph, a: SceneNode, b: SceneNode) -> float:
    ax, ay = bbox_center(a.bbox_xyxy)
    bx, by = bbox_center(b.bbox_xyxy)
    diag = _image_diagonal(graph)
    if diag <= 0:
        return 0.0
    return math.hypot(ax - bx, ay - by) / diag


def infer_image_grid_key(graph: SceneGraph, node: SceneNode) -> str:
    cx, cy = bbox_center(node.bbox_xyxy)
    x_min, x_max, y_min, y_max = _image_bounds(graph)
    col = _third_bucket(cx, x_min, x_max, axis="x")
    row = _third_bucket(cy, y_min, y_max, axis="y")
    return f"{row}_{col}"


def image_position_consistent(graph: SceneGraph, node: SceneNode) -> bool:
    manual_key = infer_manual_image_grid_key(node)
    if manual_key is None:
        return False
    return infer_image_grid_key(graph, node) == manual_key


def infer_manual_image_grid_key(node: SceneNode) -> str | None:
    labels = set(_collect_image_based_tokens(node))
    if not labels:
        return None
    if "left" in labels and "right" in labels:
        return None
    if "up" in labels and "down" in labels:
        return None
    col = "left" if "left" in labels else "right" if "right" in labels else "middle"
    row = "up" if "up" in labels else "down" if "down" in labels else "middle"
    return f"{row}_{col}"


def image_position_answer(node: SceneNode) -> tuple[str, str]:
    labels = set(_collect_image_based_tokens(node))
    if "left" in labels and "up" in labels:
        return (EN_DIRECTION["up_left"], ZH_DIRECTION["up_left"])
    if "right" in labels and "up" in labels:
        return (EN_DIRECTION["up_right"], ZH_DIRECTION["up_right"])
    if "left" in labels and "down" in labels:
        return (EN_DIRECTION["down_left"], ZH_DIRECTION["down_left"])
    if "right" in labels and "down" in labels:
        return (EN_DIRECTION["down_right"], ZH_DIRECTION["down_right"])
    if "left" in labels:
        return (EN_DIRECTION["left"], ZH_DIRECTION["left"])
    if "right" in labels:
        return (EN_DIRECTION["right"], ZH_DIRECTION["right"])
    if "up" in labels:
        return (EN_DIRECTION["up"], ZH_DIRECTION["up"])
    if "down" in labels:
        return (EN_DIRECTION["down"], ZH_DIRECTION["down"])
    return (EN_DIRECTION["middle"], ZH_DIRECTION["middle"])


def infer_image_plane_direction(target: SceneNode, anchor: SceneNode) -> ImagePlaneDirection:
    tx, ty = bbox_center(target.bbox_xyxy)
    ax, ay = bbox_center(anchor.bbox_xyxy)
    dx = tx - ax
    dy = ty - ay
    if abs(dx) < 1e-9 and abs(dy) < 1e-9:
        return ImagePlaneDirection(key="middle", en_label="overlapping", zh_label="重叠")
    ratio = abs(dx) / max(abs(dy), 1e-9)
    if ratio >= 2.0:
        if dx > 0:
            return ImagePlaneDirection(key="right", en_label="to the right", zh_label="右侧")
        return ImagePlaneDirection(key="left", en_label="to the left", zh_label="左侧")
    if ratio <= 0.5:
        if dy > 0:
            return ImagePlaneDirection(key="down", en_label="below", zh_label="下方")
        return ImagePlaneDirection(key="up", en_label="above", zh_label="上方")
    if dx > 0 and dy > 0:
        return ImagePlaneDirection(key="down_right", en_label="at the lower right", zh_label="右下方")
    if dx > 0 and dy < 0:
        return ImagePlaneDirection(key="up_right", en_label="at the upper right", zh_label="右上方")
    if dx < 0 and dy > 0:
        return ImagePlaneDirection(key="down_left", en_label="at the lower left", zh_label="左下方")
    return ImagePlaneDirection(key="up_left", en_label="at the upper left", zh_label="左上方")


def directional_answer_from_tokens(tokens: tuple[str, ...]) -> tuple[str, str]:
    normalized = list(dict.fromkeys(tokens))
    if not normalized:
        return ("unknown", "未知")
    if len(normalized) == 1:
        key = normalized[0]
        return (EN_DIRECTION.get(key, key), ZH_DIRECTION.get(key, key))
    if "left" in normalized and "up" in normalized:
        return (EN_DIRECTION["up_left"], ZH_DIRECTION["up_left"])
    if "right" in normalized and "up" in normalized:
        return (EN_DIRECTION["up_right"], ZH_DIRECTION["up_right"])
    if "left" in normalized and "down" in normalized:
        return (EN_DIRECTION["down_left"], ZH_DIRECTION["down_left"])
    if "right" in normalized and "down" in normalized:
        return (EN_DIRECTION["down_right"], ZH_DIRECTION["down_right"])
    en = " and ".join(EN_DIRECTION.get(x, x) for x in normalized)
    zh = "、".join(ZH_DIRECTION.get(x, x) for x in normalized)
    return (en, zh)


def has_orientation_relation(node: SceneNode) -> bool:
    return any(rel.relationship_type == "orientation" for rel in node.relations)


def closed_category_hit(node: SceneNode) -> bool:
    return bool(node.closed_category_hit)


def relation_tokens_between(target: SceneNode, anchor: SceneNode, relationship_type: str) -> tuple[str, ...]:
    for rel in target.relations:
        if rel.relationship_type != relationship_type:
            continue
        if rel.reference_id is None and rel.reference_label is None:
            continue
        if rel.reference_id and rel.reference_id != anchor.object_id:
            continue
        if rel.reference_label and rel.reference_label != anchor.object_label:
            continue
        values = rel.positional_tags or rel.positional_relationship
        if values:
            return tuple(values)
    return ()


def relation_tokens_self(node: SceneNode, relationship_type: str) -> tuple[str, ...]:
    for rel in node.relations:
        if rel.relationship_type != relationship_type:
            continue
        values = rel.positional_tags or rel.positional_relationship
        if values:
            return tuple(values)
    return ()


def _collect_image_based_tokens(node: SceneNode) -> list[str]:
    out: list[str] = []
    for rel in node.relations:
        if rel.relationship_type != "image-based":
            continue
        values = rel.positional_tags or rel.positional_relationship
        out.extend([v for v in values if v in IMAGE_BASED_TOKENS])
    return out


def _image_bounds(graph: SceneGraph) -> tuple[float, float, float, float]:
    if not graph.nodes:
        return (0.0, 1.0, 0.0, 1.0)
    xs1 = [n.bbox_xyxy[0] for n in graph.nodes]
    ys1 = [n.bbox_xyxy[1] for n in graph.nodes]
    xs2 = [n.bbox_xyxy[2] for n in graph.nodes]
    ys2 = [n.bbox_xyxy[3] for n in graph.nodes]
    min_x, min_y = min(xs1), min(ys1)
    max_x, max_y = max(xs2), max(ys2)
    # If bbox looks normalized already, align to [0,1] for stable 9-grid segmentation.
    if min_x >= -0.05 and min_y >= -0.05 and max_x <= 1.05 and max_y <= 1.05:
        return (0.0, 1.0, 0.0, 1.0)
    return (0.0, max(max_x, 1.0), 0.0, max(max_y, 1.0))


def _image_diagonal(graph: SceneGraph) -> float:
    x_min, x_max, y_min, y_max = _image_bounds(graph)
    return math.hypot(max(1e-9, x_max - x_min), max(1e-9, y_max - y_min))


def _third_bucket(value: float, low: float, high: float, *, axis: str) -> str:
    span = max(1e-9, high - low)
    norm = (value - low) / span
    if norm < (1.0 / 3.0):
        return "left" if axis == "x" else "up"
    if norm > (2.0 / 3.0):
        return "right" if axis == "x" else "down"
    return "middle"
