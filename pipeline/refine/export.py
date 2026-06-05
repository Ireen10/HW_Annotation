"""Optional JSONL export helper for refined samples."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from hw_annotation import AnnotationSample
from tqdm.auto import tqdm


def export_samples_jsonl(
    samples: Iterable[AnnotationSample],
    path: str | Path,
    *,
    total: int | None = None,
    show_progress: bool = True,
) -> int:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    iterator = samples
    if show_progress:
        iterator = tqdm(samples, total=total, desc="Exporting JSONL")
    with out.open("w", encoding="utf-8") as f:
        for sample in iterator:
            f.write(json.dumps(sample.to_dict(), ensure_ascii=False) + "\n")
            count += 1
    return count
