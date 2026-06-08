"""Question type enum for QA templates."""

from __future__ import annotations

from enum import Enum


class QuestionType(str, Enum):
    OPEN_ENDED = "open_ended"
    MULTIPLE_CHOICE = "multiple_choice"
    JUDGMENT = "judgment"
