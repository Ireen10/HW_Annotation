"""Import-time registration entrypoint (OpenSpatial style)."""

from . import allocentric_relation_templates  # noqa: F401
from . import egocentric_reltaion_templates  # noqa: F401
from . import image_position_templates  # noqa: F401
from . import scene_caption_templates  # noqa: F401

__all__ = [
    "scene_caption_templates",
    "image_position_templates",
    "egocentric_reltaion_templates",
    "allocentric_relation_templates",
]
