from __future__ import annotations

from typing import Any


def rectangle_to_bbox_xyxy(points: list[dict[str, Any]]) -> list[float]:
    xs = [float(p["x"]) for p in points]
    ys = [float(p["y"]) for p in points]
    return [min(xs), min(ys), max(xs), max(ys)]
