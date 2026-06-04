"""Huawei spatial annotation export tooling."""

from .dataset import HwAnnotationDataset
from .io import iter_raw_records, load_raw_records
from .normalize import parse_annotation_payload
from .sample import (
    AnnotatedObject,
    AnnotationSample,
    ImageRef,
    SpatialRelation,
    parse_sample,
)

__all__ = [
    "HwAnnotationDataset",
    "iter_raw_records",
    "load_raw_records",
    "parse_annotation_payload",
    "parse_sample",
    "AnnotationSample",
    "AnnotatedObject",
    "SpatialRelation",
    "ImageRef",
]
