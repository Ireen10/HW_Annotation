"""Pipeline configuration (override via env or CLI)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

# Closed-set categories (English) for orientation-participant objects.
DEFAULT_ORIENTATION_CLOSED_CATEGORIES: tuple[str, ...] = (
    "person",
    "humanoid_doll",
    "animal",
    "vehicle",
    "chair_with_backrest",
    "sofa_with_backrest",
    "bed",
    "desk",
    "screen",
    "other",
)

CLOSED_FALLBACK_LABEL = "other"


@dataclass(frozen=True, slots=True)
class LLMSettings:
    base_url: str = "http://127.0.0.1:8848/v1"
    model: str = "qwen3vl_32binst"
    api_key: str = "not-needed"
    timeout_s: float = 120.0
    temperature: float = 1.0

    @classmethod
    def from_env(cls) -> LLMSettings:
        defaults = cls()
        return cls(
            base_url=os.environ.get("HW_LLM_BASE_URL", defaults.base_url),
            model=os.environ.get("HW_LLM_MODEL", defaults.model),
            api_key=os.environ.get("HW_LLM_API_KEY", defaults.api_key),
            timeout_s=float(os.environ.get("HW_LLM_TIMEOUT", str(defaults.timeout_s))),
            temperature=float(os.environ.get("HW_LLM_TEMPERATURE", str(defaults.temperature))),
        )


@dataclass(frozen=True, slots=True)
class RefineConfig:
    """Settings for ``pipeline.refine``."""

    llm: LLMSettings = field(default_factory=LLMSettings.from_env)
    orientation_closed_categories: tuple[str, ...] = DEFAULT_ORIENTATION_CLOSED_CATEGORIES
    closed_fallback_label: str = CLOSED_FALLBACK_LABEL
    use_llm: bool = True
    strict_validation: bool = False
