"""Reference label → object id alignment on :class:`AnnotationSample` objects."""

from __future__ import annotations

from typing import TYPE_CHECKING

from hw_annotation.parse.sample import (
    AnnotatedObject,
    AnnotationSample,
    SpatialRelation,
    replace_object,
    replace_relation,
)
from hw_annotation.parse.types import ReferenceAlignment

if TYPE_CHECKING:
    from pipeline.utils.llm import OpenAICompatibleClient


def initial_alignment(sample: AnnotationSample) -> tuple[tuple[AnnotatedObject, ...], list[dict]]:
    by_label: dict[str, list[str]] = {}
    for obj in sample.objects:
        by_label.setdefault(obj.label, []).append(obj.id)

    issues: list[dict] = []
    refined_objects: list[AnnotatedObject] = []

    for obj in sample.objects:
        new_rels: list[SpatialRelation] = []
        for rel_index, rel in enumerate(obj.relations):
            ref_label = rel.reference_label
            ref_id = rel.reference_id
            ambiguous = rel.reference_ambiguous
            note: str | None = None
            alignment: ReferenceAlignment

            if not ref_label:
                alignment = "none"
            else:
                candidates = by_label.get(ref_label, [])
                if len(candidates) == 1:
                    alignment = "exact"
                    ref_id = candidates[0]
                elif len(candidates) > 1:
                    alignment = "ambiguous"
                    ambiguous = True
                    ref_id = ref_id or candidates[0]
                    note = f"multiple objects share label {ref_label!r}"
                    issues.append(_issue(obj.id, rel_index, ref_label, candidates, alignment, note))
                elif ref_id and not ambiguous:
                    alignment = "exact"
                else:
                    alignment = "unresolved"
                    note = f"no object label equals {ref_label!r}"
                    issues.append(
                        _issue(
                            obj.id,
                            rel_index,
                            ref_label,
                            [o.id for o in sample.objects],
                            alignment,
                            note,
                        )
                    )

            new_rels.append(
                replace_relation(
                    rel,
                    reference_id=ref_id,
                    reference_ambiguous=ambiguous,
                    reference_alignment=alignment,
                    alignment_note=note,
                )
            )
        refined_objects.append(replace_object(obj, relations=tuple(new_rels)))

    return tuple(refined_objects), issues


def _issue(
    subject_id: str,
    rel_index: int,
    reference_label: str,
    candidate_ids: list[str],
    alignment: ReferenceAlignment,
    note: str,
) -> dict:
    return {
        "issue_id": f"{subject_id}:{rel_index}",
        "subject_id": subject_id,
        "rel_index": rel_index,
        "reference_label": reference_label,
        "candidate_ids": candidate_ids,
        "current_alignment": alignment,
        "note": note,
    }


def apply_llm_alignments(
    objects: tuple[AnnotatedObject, ...],
    issues: list[dict],
    alignments: list[dict],
) -> tuple[tuple[AnnotatedObject, ...], list[str]]:
    by_issue = {a.get("issue_id"): a for a in alignments}
    notes: list[str] = []
    obj_by_id = {o.id: o for o in objects}
    updates: dict[tuple[str, int], SpatialRelation] = {}

    for issue in issues:
        issue_id = issue["issue_id"]
        result = by_issue.get(issue_id)
        subject_id = issue["subject_id"]
        rel_index = issue["rel_index"]
        rel = obj_by_id[subject_id].relations[rel_index]

        if not result:
            updates[(subject_id, rel_index)] = replace_relation(
                rel,
                reference_alignment="llm_failed",
                alignment_note="missing LLM entry",
            )
            notes.append(f"{issue_id}: missing LLM alignment")
            continue

        ref_id = result.get("reference_id")
        reason = (result.get("reason") or "").strip() or None
        if ref_id and ref_id in obj_by_id:
            updates[(subject_id, rel_index)] = replace_relation(
                rel,
                reference_id=ref_id,
                reference_alignment="llm_resolved",
                reference_ambiguous=False,
                alignment_note=reason,
            )
        else:
            updates[(subject_id, rel_index)] = replace_relation(
                rel,
                reference_alignment="llm_failed",
                alignment_note=reason or "LLM returned null or invalid reference_id",
            )
            notes.append(f"{issue_id}: unresolved after LLM")

    new_objects: list[AnnotatedObject] = []
    for obj in objects:
        new_rels = [updates.get((obj.id, i), rel) for i, rel in enumerate(obj.relations)]
        new_objects.append(replace_object(obj, relations=tuple(new_rels)))
    return tuple(new_objects), notes


def align_references_llm(
    objects: tuple[AnnotatedObject, ...],
    issues: list[dict],
    sample: AnnotationSample,
    client: OpenAICompatibleClient,
) -> tuple[tuple[AnnotatedObject, ...], list[str]]:
    from .prompts import reference_alignment_prompt

    scene = {
        "item_id": sample.item_id,
        "scenario": sample.scenario,
        "objects": [{"id": o.id, "label": o.label} for o in objects],
    }
    messages = reference_alignment_prompt(scene, issues)
    raw = client.chat(messages, json_mode=True)
    payload = client.parse_json_content(raw)
    return apply_llm_alignments(objects, issues, payload.get("alignments") or [])


def orientation_participant_ids(objects: tuple[AnnotatedObject, ...]) -> frozenset[str]:
    ids: set[str] = set()
    id_set = {o.id for o in objects}
    for obj in objects:
        for rel in obj.relations:
            if rel.relationship_type != "orientation":
                continue
            ids.add(obj.id)
            if rel.reference_id and rel.reference_id in id_set:
                ids.add(rel.reference_id)
    return frozenset(ids)


def mark_orientation_participation(objects: tuple[AnnotatedObject, ...]) -> tuple[AnnotatedObject, ...]:
    participants = orientation_participant_ids(objects)
    return tuple(
        replace_object(obj, participates_in_orientation=obj.id in participants) for obj in objects
    )
