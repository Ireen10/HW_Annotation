"""Shared type aliases for annotation samples."""

from __future__ import annotations

from typing import Literal

ReferenceAlignment = Literal[
    "none",
    "exact",
    "ambiguous",
    "unresolved",
    "llm_resolved",
    "llm_failed",
]

CategorySource = Literal["none", "closed", "open"]
