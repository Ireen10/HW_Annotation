"""Pipeline config loader and OpenSpatial-style pipeline runtime adapter."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from hw_annotation import AnnotationSample, HwAnnotationDataset, parse_sample_dict
from pipeline.base_pipeline import BasePipeline, PipelineStageResult
from pipeline.refine import export_samples_jsonl
from pipeline.task_registry import create_task


@dataclass(frozen=True, slots=True)
class StageSpec:
    name: str
    kind: str
    enabled: bool = True
    resume: bool = True
    output: str | None = None
    depends_on: str | None = None
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PipelineSpec:
    input_path: str
    artifacts_dir: str = "artifacts/pipeline"
    stages: tuple[StageSpec, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class StageResult:
    name: str
    kind: str
    output_path: str
    input_count: int
    output_count: int
    resumed: bool
    failed_count: int


@dataclass(frozen=True, slots=True)
class PipelineResult:
    samples: tuple[AnnotationSample, ...]
    stages: tuple[StageResult, ...]
    load_errors: tuple[str, ...]


def load_pipeline_spec(path: str | Path) -> PipelineSpec:
    config_path = Path(path)
    text = config_path.read_text(encoding="utf-8")
    if config_path.suffix.lower() in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("YAML config requires PyYAML; use JSON config or install pyyaml") from exc
        payload = yaml.safe_load(text)
    else:
        payload = json.loads(text)

    stage_specs = tuple(_parse_stage_spec(row) for row in payload.get("stages") or [])
    if not stage_specs:
        raise ValueError("pipeline config requires non-empty `stages`")
    return PipelineSpec(
        input_path=str(payload["input_path"]),
        artifacts_dir=str(payload.get("artifacts_dir") or "artifacts/pipeline"),
        stages=stage_specs,
    )


def build_default_pipeline_spec(
    *,
    input_path: str,
    artifacts_dir: str,
    refine_params: dict[str, Any],
) -> PipelineSpec:
    return PipelineSpec(
        input_path=input_path,
        artifacts_dir=artifacts_dir,
        stages=(StageSpec(name="refine", kind="refine", params=refine_params),),
    )


def run_pipeline(spec: PipelineSpec, *, from_stage: str | None = None) -> PipelineResult:
    dataset: HwAnnotationDataset | None = None
    load_errors: tuple[str, ...] = ()

    def load_input_samples(input_path: str) -> tuple[AnnotationSample, ...]:
        nonlocal dataset, load_errors
        if dataset is None:
            dataset = HwAnnotationDataset(input_path, status_filter=None)
            load_errors = tuple(dataset.load_errors)
        return tuple(dataset.samples())

    def read_samples(path: Path) -> tuple[AnnotationSample, ...]:
        return _load_samples_jsonl(path)

    def write_samples(samples: tuple[AnnotationSample, ...], path: Path) -> None:
        export_samples_jsonl(samples, path, total=len(samples), show_progress=False)

    pipeline = BasePipeline(
        input_path=spec.input_path,
        artifacts_dir=spec.artifacts_dir,
        stages=spec.stages,
        create_task=create_task,
        load_input_samples=load_input_samples,
        get_load_errors=lambda: load_errors,
        read_samples=read_samples,
        write_samples=write_samples,
    )
    output_samples, stage_runs, load_errors = pipeline.run(from_stage=from_stage)
    return PipelineResult(
        samples=output_samples,
        stages=tuple(_to_stage_result(r) for r in stage_runs),
        load_errors=load_errors,
    )


def _parse_stage_spec(raw: dict[str, Any]) -> StageSpec:
    return StageSpec(
        name=str(raw["name"]),
        kind=str(raw["kind"]),
        enabled=bool(raw.get("enabled", True)),
        resume=bool(raw.get("resume", True)),
        output=raw.get("output"),
        depends_on=raw.get("depends_on"),
        params=dict(raw.get("params") or {}),
    )


def _to_stage_result(result: PipelineStageResult) -> StageResult:
    return StageResult(
        name=result.name,
        kind=result.kind,
        output_path=result.output_path,
        input_count=result.input_count,
        output_count=result.output_count,
        resumed=result.resumed,
        failed_count=result.failed_count,
    )


def _load_samples_jsonl(path: Path) -> tuple[AnnotationSample, ...]:
    samples: list[AnnotationSample] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            content = line.strip()
            if not content:
                continue
            try:
                row = json.loads(content)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            samples.append(parse_sample_dict(row))
    return tuple(samples)
