"""Refine :class:`AnnotationSample` in memory for downstream pipeline modules."""

from __future__ import annotations

from typing import Iterator, Sequence

from hw_annotation import AnnotationSample
from hw_annotation.parse.sample import AnnotatedObject, replace_object, replace_relation
from hw_annotation.parse.validate_sample import validate_refined_sample
from hw_annotation.vocab.constants import DIRECTIONAL_3D_VALUES, IMAGE_BASED_VALUES, TOPOLOGY_VALUES
from pipeline.config import RefineConfig
from pipeline.utils.llm import OpenAICompatibleClient
from tqdm.auto import tqdm

from .reference import (
    initial_alignment,
    mark_orientation_participation,
)
from .tags import apply_positional_tags_rule


class RefineSampleError(RuntimeError):
    def __init__(self, item_id: str, reason: str, llm_json: object | None = None) -> None:
        super().__init__(reason)
        self.item_id = item_id
        self.reason = reason
        self.llm_json = llm_json


def _allowed_tags(rel_type: str) -> frozenset[str]:
    if rel_type == "topology":
        return TOPOLOGY_VALUES
    if rel_type == "image-based":
        return IMAGE_BASED_VALUES
    return DIRECTIONAL_3D_VALUES


def _assign_refine_fields_llm(
    sample: AnnotationSample,
    objects: tuple[AnnotatedObject, ...],
    issues: list[dict],
    client: OpenAICompatibleClient,
    config: RefineConfig,
) -> tuple[tuple[AnnotatedObject, ...], list[str], object]:
    from .prompts import unified_refine_prompt

    notes: list[str] = []
    object_ids = {o.id for o in objects}
    issue_ids = {issue["issue_id"] for issue in issues}
    allowed_closed = set(config.orientation_closed_categories)
    fallback = config.closed_fallback_label

    relation_tasks: list[dict] = []
    for obj in objects:
        for idx, rel in enumerate(obj.relations):
            issue_id = f"{obj.id}:{idx}"
            need_reference = issue_id in issue_ids
            need_tags = bool(rel.positional_relationship and not rel.positional_tags)
            if not need_reference and not need_tags:
                continue
            relation_tasks.append(
                {
                    "issue_id": issue_id,
                    "subject_id": obj.id,
                    "rel_index": idx,
                    "relationship_type": rel.relationship_type,
                    "positional_relationship": list(rel.positional_relationship),
                    "reference_label": rel.reference_label,
                    "reference_id": rel.reference_id,
                    "needs_reference_fix": need_reference,
                    "needs_positional_tags": need_tags,
                }
            )

    object_tasks = [
        {
            "object_id": obj.id,
            "label": obj.label,
            "participates_in_orientation": obj.participates_in_orientation,
            "requires_open_category": not obj.participates_in_orientation,
            "name_en": obj.name_en,
            "category_en": obj.category_en,
        }
        for obj in objects
    ]
    scene = {
        "item_id": sample.item_id,
        "scenario": sample.scenario,
        "objects": [{"id": o.id, "label": o.label} for o in objects],
    }
    messages = unified_refine_prompt(
        scene,
        object_tasks,
        relation_tasks,
        list(config.orientation_closed_categories),
        config.closed_fallback_label,
    )
    raw = client.chat(messages, json_mode=True)
    payload = client.parse_json_content(raw)

    object_map = {
        row.get("object_id"): row
        for row in (payload.get("objects") or [])
        if row.get("object_id") in object_ids
    }
    relation_map = {
        row.get("issue_id"): row
        for row in (payload.get("relations") or [])
        if row.get("issue_id")
    }

    updated_objects: list[AnnotatedObject] = []
    for obj in objects:
        row = object_map.get(obj.id, {})
        name_en = (row.get("name_en") or "").strip() or None
        if not name_en:
            notes.append(f"{obj.id}: missing name_en from LLM")

        if obj.participates_in_orientation:
            closed_cat = (row.get("closed_category_en") or "").strip() or fallback
            closed_hit = closed_cat in allowed_closed and closed_cat != fallback
            if closed_hit:
                category_en = closed_cat
                category_source = "closed"
            else:
                category_en = (row.get("category_en") or "").strip() or None
                if category_en == fallback:
                    category_en = None
                category_source = "open"
                notes.append(f"{obj.id}: closed-set fallback used")
                if not category_en and name_en:
                    category_en = name_en
                    notes.append(f"{obj.id}: open-set category fallback to name_en")
            if not category_en:
                notes.append(f"{obj.id}: missing category_en from LLM")
            new_obj = replace_object(
                obj,
                name_en=name_en,
                category_en=category_en,
                category_source=category_source,
                closed_category_en=closed_cat,
                closed_category_hit=closed_hit,
            )
        else:
            category_en = (row.get("category_en") or "").strip() or None
            if category_en == fallback:
                category_en = None
            if not category_en and name_en:
                category_en = name_en
                notes.append(f"{obj.id}: open-set category fallback to name_en")
            if not category_en:
                notes.append(f"{obj.id}: missing category_en from LLM")
            new_obj = replace_object(
                obj,
                name_en=name_en,
                category_en=category_en,
                category_source="open",
                closed_category_en=None,
                closed_category_hit=None,
            )

        new_rels = []
        for idx, rel in enumerate(new_obj.relations):
            issue_id = f"{new_obj.id}:{idx}"
            rel_row = relation_map.get(issue_id, {})
            new_rel = rel

            if issue_id in issue_ids:
                llm_ref_id = rel_row.get("reference_id")
                if isinstance(llm_ref_id, str) and llm_ref_id in object_ids:
                    new_rel = replace_relation(
                        new_rel,
                        reference_id=llm_ref_id,
                        reference_ambiguous=False,
                        reference_alignment="llm_resolved",
                        alignment_note=(rel_row.get("reason") or "").strip() or None,
                    )
                else:
                    new_rel = replace_relation(
                        new_rel,
                        reference_alignment="llm_failed",
                        alignment_note=(rel_row.get("reason") or "").strip()
                        or "LLM did not provide a valid reference_id",
                    )
                    notes.append(f"{issue_id}: unresolved after LLM")

            if rel.positional_relationship and not new_rel.positional_tags:
                llm_tags = rel_row.get("positional_tags") or []
                if isinstance(llm_tags, list):
                    allowed = _allowed_tags(new_rel.relationship_type)
                    filtered = tuple(str(t) for t in llm_tags if isinstance(t, str) and t in allowed)
                else:
                    filtered = ()
                if filtered:
                    new_rel = replace_relation(new_rel, positional_tags=filtered)
                else:
                    notes.append(f"{issue_id}: missing/invalid positional_tags from LLM")

            new_rels.append(new_rel)
        updated_objects.append(replace_object(new_obj, relations=tuple(new_rels)))
    return tuple(updated_objects), notes, payload


def refine_sample(
    sample: AnnotationSample,
    *,
    client: OpenAICompatibleClient | None,
    config: RefineConfig | None = None,
) -> AnnotationSample:
    """
    Refine one sample and return an enriched :class:`AnnotationSample` (primary API).

    Order: reference alignment → orientation flags → English names → English categories
    → positional_tags → validation.
    """
    cfg = config or RefineConfig()
    use_llm = cfg.use_llm and client is not None
    notes: list[str] = []
    llm_payload: object | None = None

    try:
        objects, issues = initial_alignment(sample)

        objects = mark_orientation_participation(objects)
        objects = apply_positional_tags_rule(objects)

        if use_llm and client is not None:
            objects, llm_notes, llm_payload = _assign_refine_fields_llm(sample, objects, issues, client, cfg)
            notes.extend(llm_notes)
        else:
            if issues:
                notes.append(f"{len(issues)} reference issue(s) remain (LLM disabled)")
            notes.append("English names/categories/positional_tags skipped (LLM disabled)")

        refined = sample.with_updates(objects=objects, is_refined=True, refine_notes=tuple(notes))

        validation_errors = validate_refined_sample(refined)
        if validation_errors:
            refined = refined.with_updates(
                refine_notes=refined.refine_notes + tuple(f"validation: {e}" for e in validation_errors)
            )
            if cfg.strict_validation:
                raise ValueError(
                    f"refine validation failed for {sample.item_id}: " + "; ".join(validation_errors)
                )

        return refined
    except RefineSampleError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise RefineSampleError(sample.item_id, str(exc), llm_json=llm_payload) from exc


def refine_dataset(
    dataset: Sequence[AnnotationSample],
    *,
    client: OpenAICompatibleClient | None,
    config: RefineConfig | None = None,
    limit: int | None = None,
    workers: int = 1,
    skip_errors: bool = True,
    errors: list[str] | None = None,
    show_progress: bool = True,
) -> list[AnnotationSample]:
    """Refine samples and return an in-memory list for downstream modules."""
    if limit is not None and limit < 0:
        raise ValueError(f"limit must be >= 0, got {limit}")
    if workers < 1:
        raise ValueError(f"workers must be >= 1, got {workers}")
    total = len(dataset)
    if limit is not None:
        total = min(total, limit)
    samples = [
        sample
        for i, sample in enumerate(dataset)
        if limit is None or i < limit
    ]

    def _record_error(sample: AnnotationSample, exc: Exception) -> None:
        if errors is None:
            return
        errors.append(f"{sample.item_id}: {exc}")

    if workers > 1:
        from concurrent.futures import ThreadPoolExecutor, as_completed

        refined: list[AnnotationSample | None] = [None] * len(samples)
        with ThreadPoolExecutor(max_workers=workers) as ex:
            future_to_idx = {
                ex.submit(refine_sample, sample, client=client, config=config): idx
                for idx, sample in enumerate(samples)
            }
            completed = as_completed(future_to_idx)
            if show_progress:
                completed = tqdm(completed, total=total, desc="Refining samples")
            for future in completed:
                idx = future_to_idx[future]
                sample = samples[idx]
                try:
                    refined[idx] = future.result()
                except Exception as exc:  # noqa: BLE001
                    if not skip_errors:
                        raise
                    _record_error(sample, exc)
        return [s for s in refined if s is not None]

    refined: list[AnnotationSample] = []
    iterator = samples
    if show_progress:
        iterator = tqdm(samples, total=total, desc="Refining samples")
    for sample in iterator:
        try:
            refined.append(refine_sample(sample, client=client, config=config))
        except Exception as exc:  # noqa: BLE001
            if not skip_errors:
                raise
            _record_error(sample, exc)
    return refined


def refine_iter(
    dataset: Sequence[AnnotationSample],
    *,
    client: OpenAICompatibleClient | None,
    config: RefineConfig | None = None,
    limit: int | None = None,
    show_progress: bool = True,
) -> Iterator[AnnotationSample]:
    if limit is not None and limit < 0:
        raise ValueError(f"limit must be >= 0, got {limit}")
    total = len(dataset)
    if limit is not None:
        total = min(total, limit)
    iterator = dataset
    if show_progress:
        iterator = tqdm(dataset, total=total, desc="Refining samples")
    for i, sample in enumerate(iterator):
        if limit is not None and i >= limit:
            break
        yield refine_sample(sample, client=client, config=config)


__all__ = ["refine_sample", "refine_dataset", "refine_iter", "RefineSampleError"]
