"""Mark planning contracts (traceable, image-independent)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class MarkSlot:
    slot_id: str
    object_id: str
    object_label: str
    mark_kind: str = "box"
    # Geometry is optional in framework stage; filled in concrete logic later.
    geometry: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class MarkPlan:
    version: int = 2
    layout: str = "per_view"
    # Keep `image_ref` for traceability; rendering is intentionally out-of-scope here.
    image_ref: str | None = None
    slots: tuple[MarkSlot, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "version": self.version,
            "layout": self.layout,
            "image_ref": self.image_ref,
            "slots": [
                {
                    "slot_id": slot.slot_id,
                    "object_id": slot.object_id,
                    "object_label": slot.object_label,
                    "mark_kind": slot.mark_kind,
                    "geometry": dict(slot.geometry),
                }
                for slot in self.slots
            ],
        }
