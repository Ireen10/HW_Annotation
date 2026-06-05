"""Vocabulary and display mappings for Huawei spatial annotation exports."""

from __future__ import annotations

RELATIONSHIP_TYPES = frozenset(
    {"topology", "image-based", "egocentric", "orientation", "allocentric"}
)

TOPOLOGY_VALUES = frozenset({"in", "on", "surround"})
IMAGE_BASED_VALUES = frozenset({"up", "down", "left", "right", "middle"})
DIRECTIONAL_3D_VALUES = frozenset(
    {"up", "down", "left", "right", "in_front_of", "behind"}
)

RELATIONSHIP_TYPE_ZH = {
    "topology": "拓扑关系",
    "image-based": "基于图片的位置关系",
    "egocentric": "观察者视角",
    "orientation": "物体朝向",
    "allocentric": "参考对象的视角",
}

POSITIONAL_ZH = {
    "in": "在……内部",
    "on": "在……上面",
    "surround": "环绕",
    "up": "上",
    "down": "下",
    "left": "左",
    "right": "右",
    "middle": "中",
    "in_front_of": "前",
    "behind": "后",
}
