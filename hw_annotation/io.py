"""Load raw JSONL export records."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator


def iter_raw_records(path: str | Path) -> Iterator[dict[str, Any]]:
    path = Path(path)
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON") from exc


def load_raw_records(path: str | Path) -> list[dict[str, Any]]:
    return list(iter_raw_records(path))
