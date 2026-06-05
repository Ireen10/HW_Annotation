"""Parse platform ``_annotation`` into lean samples."""

from .normalize import parse_annotation_payload
from .sample import (
    AnnotatedObject,
    AnnotationSample,
    ImageRef,
    SpatialRelation,
    parse_sample,
    replace_object,
    replace_relation,
)
from .validate_sample import validate_refined_sample

__all__ = [
    "parse_annotation_payload",
    "parse_sample",
    "validate_refined_sample",
    "AnnotationSample",
    "AnnotatedObject",
    "SpatialRelation",
    "ImageRef",
    "replace_object",
    "replace_relation",
]
