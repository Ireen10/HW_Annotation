"""Shared utilities (geometry, schema validation)."""

from .geometry import rectangle_to_bbox_xyxy
from .validate import validate_instance

__all__ = ["rectangle_to_bbox_xyxy", "validate_instance"]
