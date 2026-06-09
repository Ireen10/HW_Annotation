"""Scaffold QA task for spatial-relation families."""

from __future__ import annotations

import random

from pipeline.qa.base_qa_task import BaseQATask
from pipeline.qa.core import (
    QuestionType,
    SceneGraph,
    bbox_iou,
    closed_category_hit,
    directional_answer_from_tokens,
    has_orientation_relation,
    image_position_answer,
    image_position_consistent,
    infer_image_plane_direction,
    normalized_center_distance,
    relation_tokens_between,
    relation_tokens_self,
)


class SpatialRelationQATask(BaseQATask):
    SUB_TASKS = (
        "scene_caption",
        "image_position",
        "image_relative_position",
        "object_orientation",
        "egocentric_reltaion",
        "allocentric_relation",
    )

    STRICT_MIN_CENTER_DISTANCE = 0.12
    STRICT_MAX_IOU = 0.25
    CUE_PROB_EGOCENTRIC = 0.7
    WITH_CRITERION_PROB_IMAGE_POSITION = 0.9

    def resolve_template_id(
        self,
        sub_task: str,
        lang: str,
        q_type: QuestionType,
        candidate: BaseQATask.Candidate,
    ) -> str:
        suffix = "open_ended" if q_type == QuestionType.OPEN_ENDED else "multiple_choice"
        if sub_task == "image_position":
            case = str(candidate.extra.get("case") or "with_criterion")
            return f"{sub_task}.{lang}.{case}.{suffix}"
        if sub_task == "egocentric_reltaion":
            cue_case = "with_cue" if bool(candidate.extra.get("with_view_cue")) else "without_cue"
            return f"{sub_task}.{lang}.{cue_case}.{suffix}"
        return f"{sub_task}.{lang}.{suffix}"

    def question_type_ratio(self, sub_task: str) -> tuple[int, int]:
        if sub_task == "object_orientation":
            return (100, 0)
        if sub_task == "scene_caption":
            return (100, 0)
        return (80, 20)

    def iter_candidates(
        self,
        sample,
        graph: SceneGraph,
        sub_task: str,
        q_type: QuestionType,
    ) -> list[BaseQATask.Candidate]:
        del sample
        if sub_task == "scene_caption":
            return []
        if sub_task == "image_position":
            return self._iter_image_position(graph, q_type)
        if sub_task == "image_relative_position":
            return self._iter_image_relative_position(graph, q_type)
        if sub_task == "object_orientation":
            return self._iter_object_orientation(graph, q_type)
        if sub_task == "egocentric_reltaion":
            return self._iter_egocentric(graph, q_type)
        if sub_task == "allocentric_relation":
            return self._iter_allocentric(graph, q_type)
        return []

    def _iter_image_position(self, graph: SceneGraph, q_type: QuestionType) -> list[BaseQATask.Candidate]:
        out: list[BaseQATask.Candidate] = []
        for node in graph.nodes:
            if not image_position_consistent(graph, node):
                continue
            case = "with_criterion" if random.random() < self.WITH_CRITERION_PROB_IMAGE_POSITION else "without_criterion"
            ans_en, ans_zh = image_position_answer(node)
            options_en = "A. left  B. right  C. above  D. below  E. middle"
            options_zh = "A. 左边  B. 右边  C. 上方  D. 下方  E. 中间"
            out.append(
                self.Candidate(
                    question_bindings={
                        "A": node.object_label,
                        "CASE": case,
                        "OPTIONS_EN": options_en,
                        "OPTIONS_ZH": options_zh,
                    },
                    answer_bindings={
                        "X_EN": ans_en,
                        "X_ZH": ans_zh,
                    },
                    slots=(self._slot("A", node.object_id, node.object_label),),
                    extra={"q_type": q_type.value, "case": case},
                )
            )
        return out

    def _iter_image_relative_position(self, graph: SceneGraph, q_type: QuestionType) -> list[BaseQATask.Candidate]:
        out: list[BaseQATask.Candidate] = []
        for target in graph.nodes:
            for anchor in graph.nodes:
                if target.object_id == anchor.object_id:
                    continue
                if normalized_center_distance(graph, target, anchor) < self.STRICT_MIN_CENTER_DISTANCE:
                    continue
                if bbox_iou(target.bbox_xyxy, anchor.bbox_xyxy) > self.STRICT_MAX_IOU:
                    continue
                direction = infer_image_plane_direction(target, anchor)
                options_en = (
                    "A. upper-left  B. above  C. upper-right  D. left  E. right  "
                    "F. lower-left  G. below  H. lower-right"
                )
                options_zh = "A. 左上方  B. 上方  C. 右上方  D. 左侧  E. 右侧  F. 左下方  G. 下方  H. 右下方"
                out.append(
                    self.Candidate(
                        question_bindings={
                            "A": target.object_label,
                            "B": anchor.object_label,
                            "OPTIONS_EN": options_en,
                            "OPTIONS_ZH": options_zh,
                        },
                        answer_bindings={"X_EN": direction.en_label, "X_ZH": direction.zh_label},
                        slots=(
                            self._slot("A", target.object_id, target.object_label),
                            self._slot("B", anchor.object_id, anchor.object_label),
                        ),
                        extra={"q_type": q_type.value, "direction_key": direction.key},
                    )
                )
        return out

    def _iter_object_orientation(self, graph: SceneGraph, q_type: QuestionType) -> list[BaseQATask.Candidate]:
        del q_type
        out: list[BaseQATask.Candidate] = []
        for node in graph.nodes:
            orientation = relation_tokens_self(node, "orientation")
            if not orientation:
                continue
            ans_en, ans_zh = directional_answer_from_tokens(orientation)
            out.append(
                self.Candidate(
                    question_bindings={"A": node.object_label},
                    answer_bindings={"X_EN": ans_en, "X_ZH": ans_zh},
                    slots=(self._slot("A", node.object_id, node.object_label),),
                    extra={},
                )
            )
        return out

    def _iter_egocentric(self, graph: SceneGraph, q_type: QuestionType) -> list[BaseQATask.Candidate]:
        out: list[BaseQATask.Candidate] = []
        for target in graph.nodes:
            for anchor in graph.nodes:
                if target.object_id == anchor.object_id:
                    continue
                rel = relation_tokens_between(target, anchor, "egocentric")
                if not rel:
                    continue
                with_cue = random.random() < self.CUE_PROB_EGOCENTRIC
                if has_orientation_relation(anchor) and closed_category_hit(anchor):
                    with_cue = True
                viewpoint_en = "From the current perspective"
                viewpoint_zh = "从当前视角看"
                ans_en, ans_zh = directional_answer_from_tokens(rel)
                answer_bindings = {
                    "X_EN": ans_en,
                    "X_ZH": ans_zh,
                    "VIEW_EN": viewpoint_en,
                    "VIEW_ZH": viewpoint_zh,
                }
                options_en = "A. left  B. right  C. above  D. below  E. in front of  F. behind"
                options_zh = "A. 左侧  B. 右侧  C. 上方  D. 下方  E. 前方  F. 后方"
                out.append(
                    self.Candidate(
                        question_bindings={
                            "A": target.object_label,
                            "B": anchor.object_label,
                            "WITH_VIEW_CUE": "1" if with_cue else "0",
                            "VIEW_EN": viewpoint_en,
                            "VIEW_ZH": viewpoint_zh,
                            "OPTIONS_EN": options_en,
                            "OPTIONS_ZH": options_zh,
                        },
                        answer_bindings=answer_bindings,
                        slots=(
                            self._slot("A", target.object_id, target.object_label),
                            self._slot("B", anchor.object_id, anchor.object_label),
                        ),
                        extra={"with_view_cue": with_cue},
                    )
                )
        return out

    def _iter_allocentric(self, graph: SceneGraph, q_type: QuestionType) -> list[BaseQATask.Candidate]:
        out: list[BaseQATask.Candidate] = []
        for target in graph.nodes:
            for anchor in graph.nodes:
                if target.object_id == anchor.object_id:
                    continue
                rel = relation_tokens_between(target, anchor, "allocentric")
                if not rel:
                    continue
                if not has_orientation_relation(anchor):
                    continue
                if not closed_category_hit(anchor):
                    continue
                view_en, view_zh = self._allocentric_viewpoint(anchor.object_label, anchor.closed_category_en)
                ans_en, ans_zh = directional_answer_from_tokens(rel)
                answer_bindings = {
                    "X_EN": ans_en,
                    "X_ZH": ans_zh,
                    "VIEW_EN": view_en,
                    "VIEW_ZH": view_zh,
                }
                options_en = "A. left  B. right  C. above  D. below  E. in front of  F. behind"
                options_zh = "A. 左侧  B. 右侧  C. 上方  D. 下方  E. 前方  F. 后方"
                out.append(
                    self.Candidate(
                        question_bindings={
                            "A": target.object_label,
                            "B": anchor.object_label,
                            "VIEW_EN": view_en,
                            "VIEW_ZH": view_zh,
                            "OPTIONS_EN": options_en,
                            "OPTIONS_ZH": options_zh,
                        },
                        answer_bindings=answer_bindings,
                        slots=(
                            self._slot("A", target.object_id, target.object_label),
                            self._slot("B", anchor.object_id, anchor.object_label),
                        ),
                        extra={},
                    )
                )
        return out

    @staticmethod
    def _slot(slot_id: str, object_id: str, object_label: str):
        from pipeline.qa.core import MarkSlot

        return MarkSlot(slot_id=slot_id, object_id=object_id, object_label=object_label)

    def _allocentric_viewpoint(self, anchor_label: str, closed_category: str | None) -> tuple[str, str]:
        cat = (closed_category or "").strip().lower()
        if cat in {"person", "animal", "humanoid_doll", "vehicle"}:
            return (f"From {anchor_label}'s perspective", f"从{anchor_label}的视角看")
        if cat in {"chair_with_backrest", "sofa_with_backrest"}:
            return (
                f"Assume you are seated on {anchor_label}",
                f"假设你正坐在{anchor_label}上",
            )
        if cat == "bed":
            return (
                f"Assume you are at the head of {anchor_label}, facing the foot",
                f"假设你在{anchor_label}床头并朝向床尾",
            )
        if cat == "desk":
            return (
                f"Assume you are seated in front of {anchor_label}",
                f"假设你坐在{anchor_label}前",
            )
        if cat == "screen":
            return (
                f"Assume you are facing {anchor_label}",
                f"假设你正面对{anchor_label}",
            )
        return (f"From {anchor_label}'s perspective", f"从{anchor_label}的视角看")
