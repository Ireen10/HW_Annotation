"""Base QA task skeleton (framework only, no task logic)."""

from __future__ import annotations

import random
from dataclasses import dataclass

from hw_annotation import AnnotationSample
from pipeline.base_task import BaseTask, TaskRunResult

from .core import (
    MarkPlan,
    MarkSlot,
    QuestionType,
    STRUCTURED_TEMPLATE_REGISTRY,
    SceneGraph,
    TurnMetadata,
)
from .core.message_builder import create_messages

# Ensure template modules register on import.
import pipeline.prompt_templates  # noqa: F401


class BaseQATask(BaseTask):
    """Builds QA metadata skeleton and keeps samples unchanged."""

    emits_sample_output = False
    primary_artifact_names = ("qa_unrendered_records",)
    SUB_TASKS: tuple[str, ...] = ()
    LANGUAGE_OPTIONS = {"zh", "en"}
    # Shared instruction pools (task can reuse/override).
    # Free-mode is intentionally empty.
    OE_QUESTION_INSTRUCTION_PROFILES: dict[str, list[str]] = {
        "direct": [
            "Answer directly.",
            "Give the answer briefly.",
            "Reply with the key result only.",
            "Provide a short direct answer.",
            "State the answer without extra wording.",
        ],
        "sentence": [
            "Answer in a complete sentence.",
            "Reply using a full sentence.",
            "Use one complete sentence.",
            "Provide the answer as a full sentence.",
            "Respond with a complete sentence form.",
        ],
        "analyze": [
            "Show your reasoning before the answer.",
            "Give a short analysis, then answer.",
            "Explain your thinking and conclude.",
            "Provide step-by-step reasoning first.",
            "Analyze briefly, then provide the result.",
        ],
        "free": [],
    }
    MCQ_QUESTION_INSTRUCTION_PROFILES: dict[str, list[str]] = {
        "direct": [
            "Answer the correct choice directly.",
            "Reply with the correct option now.",
            "Give the right option and text.",
            "Provide the selected choice directly.",
            "Return the best option immediately.",
        ],
        "sentence": [
            "Answer in a complete sentence.",
            "Reply with a full-sentence choice statement.",
            "Use a full sentence with the chosen option.",
            "Provide the selected option in sentence form.",
            "Respond in one complete sentence.",
        ],
        "analyze": [
            "Analyze first, then choose an option.",
            "Give brief reasoning before your choice.",
            "Explain the rationale and select an option.",
            "Reason step by step, then answer.",
            "Provide analysis and the final option.",
        ],
        "free": [],
    }

    @dataclass(frozen=True, slots=True)
    class Candidate:
        question_bindings: dict[str, str]
        answer_bindings: dict[str, str]
        slots: tuple[MarkSlot, ...]
        extra: dict[str, object]

    def run(self, samples: tuple[AnnotationSample, ...]) -> TaskRunResult:
        qa_records: list[dict[str, object]] = []
        lang = self._resolve_lang()
        for sample in samples:
            graph = SceneGraph.from_sample(sample)
            qa_records.extend(self.build_sample_records(sample, graph, lang=lang))

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
        *,
        lang: str,
    ) -> list[dict[str, object]]:
        records: list[dict[str, object]] = []
        sub_task_counts = self._resolve_sub_task_counts()
        for sub_task in self.SUB_TASKS:
            target = sub_task_counts.get(sub_task, 1)
            seen_keys: set[str] = set()
            produced = 0
            max_attempts = max(target * 8, 8)
            attempts = 0
            while produced < target and attempts < max_attempts:
                q_type = self.choose_question_type(sub_task)
                candidate = self.pick_candidate(sample, graph, sub_task, q_type)
                attempts += 1
                if candidate is None:
                    break
                rec = self.build_subtask_record(
                    sample,
                    graph,
                    sub_task,
                    q_type,
                    candidate,
                    lang=lang,
                )
                if rec is None:
                    break
                dedup_key = self._sampling_dedup_key(rec)
                if dedup_key in seen_keys:
                    continue
                seen_keys.add(dedup_key)
                records.append(rec)
                produced += 1
        return records

    def choose_question_type(self, sub_task: str) -> QuestionType:
        oe_ratio, mcq_ratio = self.question_type_ratio(sub_task)
        total = oe_ratio + mcq_ratio
        if total <= 0:
            return QuestionType.OPEN_ENDED
        threshold = oe_ratio / total
        return QuestionType.OPEN_ENDED if random.random() < threshold else QuestionType.MULTIPLE_CHOICE

    def question_type_ratio(self, sub_task: str) -> tuple[int, int]:
        del sub_task
        return (100, 0)

    def pick_candidate(
        self,
        sample: AnnotationSample,
        graph: SceneGraph,
        sub_task: str,
        q_type: QuestionType,
    ) -> Candidate | None:
        candidates = self.iter_candidates(sample, graph, sub_task, q_type)
        if not candidates:
            return None
        return random.choice(candidates)

    def iter_candidates(
        self,
        sample: AnnotationSample,
        graph: SceneGraph,
        sub_task: str,
        q_type: QuestionType,
    ) -> list[Candidate]:
        del sample, sub_task, q_type
        slot_a = graph.nodes[0] if graph.nodes else None
        slot_b = graph.nodes[1] if len(graph.nodes) > 1 else None

        question_bindings: dict[str, str] = {}
        slots: list[MarkSlot] = []
        if slot_a is not None:
            question_bindings["A"] = slot_a.object_label
            slots.append(MarkSlot(slot_id="A", object_id=slot_a.object_id, object_label=slot_a.object_label))
        if slot_b is not None:
            question_bindings["B"] = slot_b.object_label
            slots.append(MarkSlot(slot_id="B", object_id=slot_b.object_id, object_label=slot_b.object_label))
        if not slots:
            return []
        return [
            self.Candidate(
                question_bindings=question_bindings,
                answer_bindings={},
                slots=tuple(slots),
                extra={},
            )
        ]

    def _template_id(self, sub_task: str, lang: str, q_type: QuestionType) -> str:
        suffix = "open_ended" if q_type == QuestionType.OPEN_ENDED else "multiple_choice"
        return f"{sub_task}.{lang}.{suffix}"

    def resolve_template_id(
        self,
        sub_task: str,
        lang: str,
        q_type: QuestionType,
        candidate: Candidate,
    ) -> str:
        del candidate
        return self._template_id(sub_task, lang, q_type)

    def build_subtask_record(
        self,
        sample: AnnotationSample,
        graph: SceneGraph,
        sub_task: str,
        q_type: QuestionType,
        candidate: Candidate,
        *,
        lang: str,
    ) -> dict[str, object] | None:
        template = STRUCTURED_TEMPLATE_REGISTRY.get(self.resolve_template_id(sub_task, lang, q_type, candidate))
        render = template.render(
            question_bindings=candidate.question_bindings,
            answer_bindings=candidate.answer_bindings,
        )
        mark_plan = MarkPlan(image_ref=graph.image_ref, slots=candidate.slots)
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
        # In-task dedup key: same task + question type + same unordered object group.
        import json

        item_id = str(record.get("item_id") or "")
        sub_task = str(record.get("sub_task") or "")
        question_type = str((record.get("template") or {}).get("question_type") or "")
        mark_spec = record.get("mark_spec") or {}
        slots = (mark_spec.get("slots") if isinstance(mark_spec, dict) else None) or []
        obj_ids = sorted({str(s.get("object_id") or "") for s in slots if isinstance(s, dict)})
        return json.dumps(
            {"item_id": item_id, "sub_task": sub_task, "question_type": question_type, "object_group": obj_ids},
            ensure_ascii=False,
            sort_keys=True,
        )

    def _resolve_lang(self) -> str:
        raw = str(self.params.get("lang", "en")).strip().lower()
        if raw not in self.LANGUAGE_OPTIONS:
            raise ValueError(f"unsupported qa lang={raw!r}; expected one of {sorted(self.LANGUAGE_OPTIONS)}")
        return raw
