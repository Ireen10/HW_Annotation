"""Refine :class:`AnnotationSample` in memory for downstream pipeline modules."""

from __future__ import annotations

from typing import Iterator

from hw_annotation import AnnotationSample, HwAnnotationDataset
from hw_annotation.parse.validate_sample import validate_refined_sample
from pipeline.config import RefineConfig
from pipeline.utils.llm import LLMError, OpenAICompatibleClient

from .categories import assign_categories
from .names import assign_english_names
from .reference import (
    align_references_llm,
    initial_alignment,
    mark_orientation_participation,
)
from .tags import (
    apply_positional_tags_rule,
    assign_positional_tags_llm,
)


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

    objects, issues = initial_alignment(sample)

    if issues:
        if use_llm and client is not None:
            objects, align_notes = align_references_llm(objects, issues, sample, client)
            notes.extend(align_notes)
        else:
            notes.append(f"{len(issues)} reference issue(s) remain (LLM disabled)")

    objects = mark_orientation_participation(objects)

    if use_llm and client is not None:
        objects, name_notes = assign_english_names(sample, objects, client)
        notes.extend(name_notes)
        objects, cat_notes = assign_categories(sample, objects, client, cfg)
        notes.extend(cat_notes)
    else:
        notes.append("English names/categories skipped (LLM disabled)")

    objects = apply_positional_tags_rule(objects)
    if use_llm and client is not None:
        objects, tag_notes = assign_positional_tags_llm(sample, objects, client)
        notes.extend(tag_notes)
    else:
        notes.append("positional_tags LLM pass skipped (LLM disabled)")

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


def refine_dataset(
    dataset: HwAnnotationDataset,
    *,
    client: OpenAICompatibleClient | None,
    config: RefineConfig | None = None,
    limit: int | None = None,
) -> list[AnnotationSample]:
    """Refine samples and return an in-memory list for downstream modules."""
    if limit is not None and limit < 0:
        raise ValueError(f"limit must be >= 0, got {limit}")
    return [
        refine_sample(s, client=client, config=config)
        for i, s in enumerate(dataset)
        if limit is None or i < limit
    ]


def refine_iter(
    dataset: HwAnnotationDataset,
    *,
    client: OpenAICompatibleClient | None,
    config: RefineConfig | None = None,
    limit: int | None = None,
) -> Iterator[AnnotationSample]:
    if limit is not None and limit < 0:
        raise ValueError(f"limit must be >= 0, got {limit}")
    for i, sample in enumerate(dataset):
        if limit is not None and i >= limit:
            break
        yield refine_sample(sample, client=client, config=config)


__all__ = ["refine_sample", "refine_dataset", "refine_iter", "LLMError"]
