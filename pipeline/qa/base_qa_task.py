"""Base QA task skeleton (framework only, no task logic)."""

from __future__ import annotations

from hw_annotation import AnnotationSample
from pipeline.base_task import BaseTask, TaskRunResult

from .core import (
    MarkPlan,
    MarkSlot,
    STRUCTURED_TEMPLATE_REGISTRY,
    SceneGraph,
    TurnMetadata,
)
from .core.message_builder import create_messages

# Ensure template modules register on import.
import pipeline.prompt_templates  # noqa: F401


class BaseQATask(BaseTask):
    """Builds QA metadata skeleton and keeps samples unchanged."""

    SUB_TASKS: tuple[str, ...] = ()

    def run(self, samples: tuple[AnnotationSample, ...]) -> TaskRunResult:
        qa_records: list[dict[str, object]] = []
        for sample in samples:
            graph = SceneGraph.from_sample(sample)
            qa_records.extend(self.build_sample_records(sample, graph))

        # Framework stage: keep `AnnotationSample` untouched; write QA as sidecar artifact.
        return TaskRunResult(
            samples=tuple(samples),
            artifacts={"qa_unrendered_records": qa_records},
            notes=("framework_only_no_task_logic",),
        )

    def build_sample_records(
        self,
        sample: AnnotationSample,
        graph: SceneGraph,
    ) -> list[dict[str, object]]:
        records: list[dict[str, object]] = []
        sub_task_counts = self._resolve_sub_task_counts()
        for sub_task in self.SUB_TASKS:
            target = sub_task_counts.get(sub_task, 1)
            seen_keys: set[str] = set()
            attempts = 0
            max_attempts = max(target * 8, 8)
            while len([r for r in records if r.get("sub_task") == sub_task]) < target and attempts < max_attempts:
                rec = self.build_subtask_record(sample, graph, sub_task)
                attempts += 1
                if rec is None:
                    break
                dedup_key = self._sampling_dedup_key(rec)
                if dedup_key in seen_keys:
                    continue
                seen_keys.add(dedup_key)
                records.append(rec)
        return records

    def build_subtask_record(
        self,
        sample: AnnotationSample,
        graph: SceneGraph,
        sub_task: str,
    ) -> dict[str, object] | None:
        # Placeholder-only scaffold. Concrete generation logic is intentionally deferred.
        template = STRUCTURED_TEMPLATE_REGISTRY.get(f"{sub_task}.open_ended")
        slot_a = graph.nodes[0] if graph.nodes else None
        slot_b = graph.nodes[1] if len(graph.nodes) > 1 else None

        question_bindings: dict[str, str] = {}
        answer_bindings: dict[str, str] = {}
        slots: list[MarkSlot] = []
        if slot_a is not None:
            question_bindings["A"] = slot_a.object_label
            slots.append(MarkSlot(slot_id="A", object_id=slot_a.object_id, object_label=slot_a.object_label))
        if slot_b is not None:
            question_bindings["B"] = slot_b.object_label
            slots.append(MarkSlot(slot_id="B", object_id=slot_b.object_id, object_label=slot_b.object_label))

        render = template.render(question_bindings=question_bindings, answer_bindings=answer_bindings)
        mark_plan = MarkPlan(image_ref=graph.image_ref, slots=tuple(slots))
        turn_meta = TurnMetadata(
            item_id=sample.item_id,
            task_name=sub_task,
            template_id=template.template_id,
            question_type=render.question_type.value,
            introduction_pattern=render.introduction_line,
            question_pattern=render.stem_line,
            question_instruction_pattern=render.question_instruction_line,
            answer_pattern=render.answer_line,
            question_bindings=render.question_bindings,
            answer_bindings=render.answer_bindings,
            mark_spec=mark_plan.to_dict(),
        )

        return {
            "item_id": sample.item_id,
            "sub_task": sub_task,
            "template": render.to_dict(),
            "messages": create_messages(render.question_text, render.answer_text),
            "mark_spec": mark_plan.to_dict(),
            "metadata": turn_meta.to_dict(),
        }

    def _resolve_sub_task_counts(self) -> dict[str, int]:
        raw = self.params.get("sub_tasks")
        if not isinstance(raw, dict):
            return {name: 1 for name in self.SUB_TASKS}
        out: dict[str, int] = {name: 1 for name in self.SUB_TASKS}
        for name in self.SUB_TASKS:
            value = raw.get(name)
            if value is None:
                continue
            out[name] = max(0, int(value))
        return out

    def _sampling_dedup_key(self, record: dict[str, object]) -> str:
        # In-task dedup key: same task + same unordered object group.
        import json

        item_id = str(record.get("item_id") or "")
        sub_task = str(record.get("sub_task") or "")
        mark_spec = record.get("mark_spec") or {}
        slots = (mark_spec.get("slots") if isinstance(mark_spec, dict) else None) or []
        obj_ids = sorted({str(s.get("object_id") or "") for s in slots if isinstance(s, dict)})
        return json.dumps(
            {"item_id": item_id, "sub_task": sub_task, "object_group": obj_ids},
            ensure_ascii=False,
            sort_keys=True,
        )
