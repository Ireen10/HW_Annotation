"""Stage-based pipeline runtime with artifact-backed resume."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from hw_annotation import AnnotationSample, HwAnnotationDataset, parse_sample_dict
from pipeline.config import LLMSettings, RefineConfig
from pipeline.refine import export_samples_jsonl, refine_dataset
from pipeline.utils.llm import OpenAICompatibleClient


@dataclass(frozen=True, slots=True)
class StageSpec:
    name: str
    kind: str
    enabled: bool = True
    resume: bool = True
    output: str | None = None
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
    enabled = [stage for stage in spec.stages if stage.enabled]
    if not enabled:
        raise ValueError("no enabled stages in pipeline")
    names = [stage.name for stage in enabled]
    if len(set(names)) != len(names):
        raise ValueError(f"duplicate stage names found: {names}")

    start_idx = 0
    if from_stage is not None:
        try:
            start_idx = names.index(from_stage)
        except ValueError as exc:
            raise ValueError(f"from_stage {from_stage!r} not found in enabled stages {names}") from exc

    artifacts_root = Path(spec.artifacts_dir)
    artifacts_root.mkdir(parents=True, exist_ok=True)

    dataset: HwAnnotationDataset | None = None
    load_errors: tuple[str, ...] = ()
    current_samples: tuple[AnnotationSample, ...] | None = None
    stage_results: list[StageResult] = []

    def ensure_input_loaded() -> tuple[AnnotationSample, ...]:
        nonlocal dataset, load_errors
        if dataset is None:
            dataset = HwAnnotationDataset(spec.input_path, status_filter=None)
            load_errors = tuple(dataset.load_errors)
            return tuple(dataset.samples())
        return tuple(dataset.samples())

    output_paths = [_stage_output_path(artifacts_root, stage, idx) for idx, stage in enumerate(enabled)]

    for idx, stage in enumerate(enabled):
        output_path = output_paths[idx]
        if idx < start_idx:
            continue

        if current_samples is None:
            if idx == 0:
                current_samples = ensure_input_loaded()
            else:
                prev_path = output_paths[idx - 1]
                if not prev_path.is_file():
                    raise FileNotFoundError(
                        f"cannot start from stage {stage.name!r}: missing previous artifact {prev_path}"
                    )
                current_samples = _load_samples_jsonl(prev_path)

        input_count = len(current_samples)
        resumed = stage.resume and output_path.is_file()
        failed_count = 0
        if resumed:
            output_samples = _load_samples_jsonl(output_path)
        else:
            output_samples, failed_count = _run_stage(stage, current_samples)
            export_samples_jsonl(output_samples, output_path, total=len(output_samples), show_progress=False)

        current_samples = tuple(output_samples)
        stage_results.append(
            StageResult(
                name=stage.name,
                kind=stage.kind,
                output_path=str(output_path),
                input_count=input_count,
                output_count=len(current_samples),
                resumed=resumed,
                failed_count=failed_count,
            )
        )

    if current_samples is None:
        # This branch only occurs when all enabled stages were skipped by from_stage.
        current_samples = ensure_input_loaded()

    return PipelineResult(samples=current_samples, stages=tuple(stage_results), load_errors=load_errors)


def _parse_stage_spec(raw: dict[str, Any]) -> StageSpec:
    return StageSpec(
        name=str(raw["name"]),
        kind=str(raw["kind"]),
        enabled=bool(raw.get("enabled", True)),
        resume=bool(raw.get("resume", True)),
        output=raw.get("output"),
        params=dict(raw.get("params") or {}),
    )


def _stage_output_path(root: Path, stage: StageSpec, stage_idx: int) -> Path:
    filename = stage.output or "data.jsonl"
    stage_dir = root / f"{stage_idx + 1:02d}_{stage.name}"
    return stage_dir / filename


def _run_stage(
    stage: StageSpec,
    inputs: tuple[AnnotationSample, ...],
) -> tuple[tuple[AnnotationSample, ...], int]:
    if stage.kind != "refine":
        raise ValueError(f"unsupported stage kind: {stage.kind!r}")
    params = stage.params
    llm_cfg = LLMSettings()
    if params.get("llm_base_url") or params.get("llm_model"):
        llm_cfg = replace(
            llm_cfg,
            base_url=str(params.get("llm_base_url") or llm_cfg.base_url),
            model=str(params.get("llm_model") or llm_cfg.model),
        )
    refine_cfg = RefineConfig(
        llm=llm_cfg,
        use_llm=bool(params.get("use_llm", True)),
        strict_validation=bool(params.get("strict_validation", False)),
    )
    client: OpenAICompatibleClient | None = None
    if refine_cfg.use_llm:
        client = OpenAICompatibleClient(refine_cfg.llm)
    errors: list[str] = []
    refined = refine_dataset(
        inputs,
        client=client,
        config=refine_cfg,
        limit=params.get("limit"),
        workers=int(params.get("workers", 1)),
        skip_errors=not bool(params.get("fail_fast", False)),
        errors=errors,
    )
    return tuple(refined), len(errors)


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
