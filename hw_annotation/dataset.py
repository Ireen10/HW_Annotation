"""Dataloader for Huawei spatial annotation JSONL exports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator, Sequence

from .io import iter_raw_records
from .sample import AnnotationSample, parse_sample


class HwAnnotationDataset:
    """
    Load human annotation exports from a ``.jsonl`` file (or directory of ``*.jsonl``).

    Each index yields an :class:`AnnotationSample` with scenario, objects, bboxes, and
    relations. Platform fields (worker id, timestamps, UI state, repeated guidelines)
    are not stored on the sample.

    Use :attr:`guidelines_text` for the shared annotation instruction block (loaded once).
    """

    def __init__(
        self,
        path: str | Path,
        *,
        status_filter: Sequence[str] | None = ("MERGED",),
        batch_filter: Sequence[str] | None = None,
    ) -> None:
        self.path = Path(path)
        self.status_filter = frozenset(status_filter) if status_filter is not None else None
        self.batch_filter = frozenset(batch_filter) if batch_filter is not None else None
        self._samples: list[AnnotationSample] | None = None
        self._guidelines_text: str | None = None
        self._load_errors: list[str] = []

    def _iter_source_paths(self) -> Iterator[Path]:
        if self.path.is_file():
            yield self.path
            return
        if self.path.is_dir():
            for p in sorted(self.path.glob("*.jsonl")):
                yield p
            return
        raise FileNotFoundError(self.path)

    def _accept_raw(self, record: dict) -> bool:
        if self.status_filter is not None:
            if record.get("_annot_status") not in self.status_filter:
                return False
        if self.batch_filter is not None:
            if record.get("batch") not in self.batch_filter:
                return False
        return True

    def _load_all(self) -> list[AnnotationSample]:
        if self._samples is not None:
            return self._samples

        samples: list[AnnotationSample] = []
        guidelines_set = False

        for jsonl_path in self._iter_source_paths():
            for record in iter_raw_records(jsonl_path):
                if not guidelines_set and record.get("text"):
                    self._guidelines_text = record["text"]
                    guidelines_set = True

                if not self._accept_raw(record):
                    continue

                try:
                    samples.append(parse_sample(record))
                except (ValueError, KeyError, json.JSONDecodeError) as exc:
                    self._load_errors.append(
                        f"{record.get('item_id', '?')} ({jsonl_path.name}): {exc}"
                    )

        self._samples = samples
        return samples

    @property
    def guidelines_text(self) -> str | None:
        """Annotation guideline text (identical across rows); loaded once, not per sample."""
        self._load_all()
        return self._guidelines_text

    @property
    def load_errors(self) -> list[str]:
        self._load_all()
        return list(self._load_errors)

    def __len__(self) -> int:
        return len(self._load_all())

    def __getitem__(self, index: int) -> AnnotationSample:
        return self._load_all()[index]

    def __iter__(self) -> Iterator[AnnotationSample]:
        yield from self._load_all()

    def samples(self) -> list[AnnotationSample]:
        return list(self._load_all())
