"""Message builder for unrendered QA samples."""

from __future__ import annotations


def create_messages(question_text: str, answer_text: str) -> list[dict[str, str]]:
    return [
        {"from": "human", "value": question_text},
        {"from": "gpt", "value": answer_text},
    ]
