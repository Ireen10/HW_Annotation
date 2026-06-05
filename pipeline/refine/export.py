"""Optional JSONL export helper for refined samples."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from hw_annotation import AnnotationSample


def export_samples_jsonl(samples: Iterable[AnnotationSample], path: str | Path) -> int:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with out.open("w", encoding="utf-8") as f:
        for sample in samples:
            f.write(json.dumps(sample.to_dict(), ensure_ascii=False) + "\n")
            count += 1
    return count
