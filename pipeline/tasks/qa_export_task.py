"""Export merged QA records into sharded JSONL + tar bundle."""

from __future__ import annotations

import json
from pathlib import Path

from pipeline.base_task import BaseTask, TaskRunResult
from pipeline.export import DEFAULT_SHARD_SIZE, write_sharded_bundle


class QAExportTask(BaseTask):
    def run(self, samples: tuple) -> TaskRunResult:
        input_source = self.runtime_context.get("input_source_path")
        output_dir = self.runtime_context.get("stage_output_dir")
        if not input_source or not output_dir:
            raise ValueError("qa_export requires runtime context paths")

        merged_path = self.params.get("merged_records_path") or _sibling_artifact_path(
            str(input_source), "qa_merged_records.jsonl"
        )
        merged_records = _load_jsonl_records(str(merged_path))

        shard_size = int(self.params.get("shard_size") or DEFAULT_SHARD_SIZE)
        image_root = self.params.get("image_root")
        stats = write_sharded_bundle(
            merged_records,
            output_root=str(Path(output_dir) / "bundle"),
            shard_size=shard_size,
            image_root=str(image_root) if image_root else None,
        )
        return TaskRunResult(samples=tuple(samples), artifacts={"export_stats": stats})


def _sibling_artifact_path(input_source_path: str, filename: str) -> str:
    return str(Path(input_source_path).parent / filename)


def _load_jsonl_records(path: str) -> list[dict]:
    rows: list[dict] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            text = line.strip()
            if not text:
                continue
            rows.append(json.loads(text))
    return rows
