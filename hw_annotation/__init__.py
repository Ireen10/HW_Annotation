"""Huawei spatial annotation export tooling."""

from .loader import HwAnnotationDataset, iter_raw_records, load_raw_records
from .parse import (
    AnnotatedObject,
    AnnotationSample,
    ImageRef,
    SpatialRelation,
    parse_annotation_payload,
    parse_sample,
    parse_sample_dict,
    validate_refined_sample,
)

__all__ = [
    "HwAnnotationDataset",
    "iter_raw_records",
    "load_raw_records",
    "parse_annotation_payload",
    "parse_sample",
    "parse_sample_dict",
    "validate_refined_sample",
    "AnnotationSample",
    "AnnotatedObject",
    "SpatialRelation",
    "ImageRef",
]
