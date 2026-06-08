"""Deduplicate and merge QA turns into multi-turn samples."""

from __future__ import annotations

import json
import uuid
from collections import defaultdict

from pipeline.base_task import BaseTask, TaskRunResult


class QAAggregateTask(BaseTask):
    """Post-QA aggregator: dedup within task, then merge by image+mark."""

    def run(self, samples: tuple) -> TaskRunResult:
        input_source = self.runtime_context.get("input_source_path")
        if not input_source:
            raise ValueError("qa_aggregate requires input_source_path context")
        qa_path = self.params.get("qa_records_path") or _sibling_artifact_path(
            str(input_source), "qa_unrendered_records.jsonl"
        )

        turns = _load_jsonl_records(str(qa_path))
        deduped = _dedup_turns(turns)
        merged = _merge_turns(deduped)
        return TaskRunResult(
            samples=tuple(samples),
            artifacts={
                "qa_deduped_records": deduped,
                "qa_merged_records": merged,
            },
        )


def _sibling_artifact_path(input_source_path: str, filename: str) -> str:
    import os

    stage_dir = os.path.dirname(input_source_path)
    return os.path.join(stage_dir, filename)


def _load_jsonl_records(path: str) -> list[dict]:
    records: list[dict] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            text = line.strip()
            if not text:
                continue
            records.append(json.loads(text))
    return records


def _dedup_turns(records: list[dict]) -> list[dict]:
    # Keep first turn per (item, task, unordered-object-group).
    grouped: dict[str, dict] = {}
    for rec in records:
        key = _dedup_key(rec)
        grouped.setdefault(key, rec)
    return list(grouped.values())


def _dedup_key(rec: dict) -> str:
    item_id = str(rec.get("item_id") or "")
    task_name = str(rec.get("sub_task") or "")
    object_ids = []
    for slot in ((rec.get("mark_spec") or {}).get("slots") or []):
        obj_id = slot.get("object_id")
        if obj_id is not None:
            object_ids.append(str(obj_id))
    # Order-insensitive object-group signature (A,B == B,A).
    signature = sorted(set(object_ids))
    return json.dumps(
        {"item_id": item_id, "task_name": task_name, "object_group": signature},
        ensure_ascii=False,
        sort_keys=True,
    )


def _merge_turns(records: list[dict]) -> list[dict]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for rec in records:
        groups[_merge_group_key(rec)].append(rec)

    merged_rows: list[dict] = []
    for group_key, turns in groups.items():
        first = turns[0]
        merged_messages: list[dict] = []
        for turn in turns:
            merged_messages.extend(turn.get("messages") or [])

        merged_rows.append(
            {
                "schema_version": "1.0",
                "sample_id": str(uuid.uuid4()),
                "merge_group_key": group_key,
                "item_id": first.get("item_id"),
                "image_ref": (first.get("mark_spec") or {}).get("image_ref"),
                "messages": merged_messages,
                "metadata": {
                    "turn_count": len(turns),
                    "source_tasks": sorted({str(t.get("sub_task") or "") for t in turns}),
                    "mark_spec": first.get("mark_spec"),
                    "turns": [t.get("metadata") for t in turns],
                },
            }
        )
    return merged_rows


def _merge_group_key(rec: dict) -> str:
    item_id = str(rec.get("item_id") or "")
    mark_spec = rec.get("mark_spec") or {}
    image_ref = mark_spec.get("image_ref")
    slots = mark_spec.get("slots") or []
    norm_slots = sorted(
        [
            {
                "object_id": str(s.get("object_id") or ""),
                "mark_kind": str(s.get("mark_kind") or ""),
            }
            for s in slots
        ],
        key=lambda x: (x["object_id"], x["mark_kind"]),
    )
    return json.dumps(
        {"item_id": item_id, "image_ref": image_ref, "slots": norm_slots},
        ensure_ascii=False,
        sort_keys=True,
    )
