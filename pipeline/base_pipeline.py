"""OpenSpatial-style base pipeline executor."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from hw_annotation import AnnotationSample

from .base_task import BaseTask


@dataclass(frozen=True, slots=True)
class PipelineStageResult:
    name: str
    kind: str
    output_path: str
    input_count: int
    output_count: int
    resumed: bool
    failed_count: int


class BasePipeline:
    def __init__(
        self,
        *,
        input_path: str,
        artifacts_dir: str,
        stages: tuple,
        create_task: Callable[[str, str, dict], BaseTask],
        load_input_samples: Callable[[str], tuple[AnnotationSample, ...]],
        get_load_errors: Callable[[], tuple[str, ...]],
        read_samples: Callable[[Path], tuple[AnnotationSample, ...]],
        write_samples: Callable[[tuple[AnnotationSample, ...], Path], None],
    ) -> None:
        self.input_path = input_path
        self.artifacts_root = Path(artifacts_dir)
        self.stages = tuple(stage for stage in stages if stage.enabled)
        self.create_task = create_task
        self.load_input_samples = load_input_samples
        self.get_load_errors = get_load_errors
        self.read_samples = read_samples
        self.write_samples = write_samples

        self.artifacts_root.mkdir(parents=True, exist_ok=True)
        self.output_paths = [self._stage_output_path(stage, idx) for idx, stage in enumerate(self.stages)]
        self.stage_name_to_idx = {stage.name: idx for idx, stage in enumerate(self.stages)}
        self.tasks = [
            self.create_task(stage.kind, stage.name, stage.params)
            for stage in self.stages
        ]

    def run(
        self,
        *,
        from_stage: str | None = None,
    ) -> tuple[tuple[AnnotationSample, ...], tuple[PipelineStageResult, ...], tuple[str, ...]]:
        if not self.stages:
            raise ValueError("no enabled stages in pipeline")

        start_idx = 0
        if from_stage is not None:
            try:
                start_idx = self.stage_name_to_idx[from_stage]
            except KeyError as exc:
                names = [stage.name for stage in self.stages]
                raise ValueError(f"from_stage {from_stage!r} not found in enabled stages {names}") from exc

        current_samples: tuple[AnnotationSample, ...] | None = None
        input_source_path: Path | None = None
        results: list[PipelineStageResult] = []

        for idx, (stage, task) in enumerate(zip(self.stages, self.tasks, strict=True)):
            if idx < start_idx:
                continue
            output_path = self.output_paths[idx]

            if current_samples is None:
                current_samples, input_source_path = self._load_stage_input(idx)
            else:
                prev_output = self.output_paths[idx - 1]
                prev_task = self.tasks[idx - 1]
                input_source_path = (
                    prev_output if prev_task.emits_sample_output else prev_output.parent
                )

            input_count = len(current_samples)
            resumed = stage.resume and self._stage_output_ready(task, output_path)
            task.set_runtime_context(
                stage_name=stage.name,
                stage_kind=stage.kind,
                input_source_path=str(input_source_path) if input_source_path is not None else None,
                stage_output_dir=str(output_path.parent),
                output_path=str(output_path),
                artifacts_root=str(self.artifacts_root),
                resume_requested=resumed,
            )
            if resumed and not task.incremental_resume_capable:
                if task.emits_sample_output:
                    output_samples = self.read_samples(output_path)
                else:
                    output_samples = current_samples
                failed_count = 0
            else:
                run_result = task.run(current_samples)
                output_samples = run_result.samples
                failed_count = run_result.failed_count
                if task.emits_sample_output and not run_result.wrote_main_output:
                    self.write_samples(output_samples, output_path)
                self._write_task_artifacts(output_path.parent, run_result.artifacts)

            current_samples = output_samples
            results.append(
                PipelineStageResult(
                    name=stage.name,
                    kind=stage.kind,
                    output_path=str(output_path),
                    input_count=input_count,
                    output_count=len(output_samples),
                    resumed=resumed,
                    failed_count=failed_count,
                )
            )

        if current_samples is None:
            current_samples = self.load_input_samples(self.input_path)

        return current_samples, tuple(results), self.get_load_errors()

    def _load_stage_input(self, stage_idx: int) -> tuple[tuple[AnnotationSample, ...], Path | None]:
        stage = self.stages[stage_idx]
        depends_on = getattr(stage, "depends_on", None)
        if depends_on:
            dep_path = self._resolve_dependency_path(depends_on, stage_idx)
            return self.read_samples(dep_path), dep_path
        if stage_idx == 0:
            return self.load_input_samples(self.input_path), None
        prev = self.output_paths[stage_idx - 1]
        return self.read_samples(prev), prev

    def _resolve_dependency_path(self, depends_on: str, stage_idx: int) -> Path:
        depends = Path(depends_on)
        if depends.is_file():
            return depends
        if depends.suffix:
            candidate = self.artifacts_root / depends
            if candidate.is_file():
                return candidate
        if depends_on in self.stage_name_to_idx:
            dep_idx = self.stage_name_to_idx[depends_on]
            if dep_idx >= stage_idx:
                raise ValueError(f"depends_on must reference a previous stage: {depends_on!r}")
            return self.output_paths[dep_idx]
        raise FileNotFoundError(f"cannot resolve depends_on={depends_on!r}")

    def _stage_output_path(self, stage, stage_idx: int) -> Path:
        filename = stage.output or "data.jsonl"
        task_name = str((stage.params or {}).get("task_name") or stage.kind)
        return self.artifacts_root / stage.name / task_name / filename

    def _stage_output_ready(self, task: BaseTask, output_path: Path) -> bool:
        if task.emits_sample_output:
            return output_path.is_file()
        stage_dir = output_path.parent
        for name in task.primary_artifact_names:
            if (stage_dir / f"{name}.jsonl").is_file():
                return True
            if (stage_dir / f"{name}.json").is_file():
                return True
            if (stage_dir / name / "metadata.json").is_file():
                return True
        return False

    def _write_task_artifacts(self, stage_dir: Path, artifacts: dict[str, object]) -> None:
        if not artifacts:
            return
        stage_dir.mkdir(parents=True, exist_ok=True)
        for name, payload in artifacts.items():
            if isinstance(payload, list):
                path = stage_dir / f"{name}.jsonl"
                with path.open("w", encoding="utf-8") as f:
                    for row in payload:
                        f.write(json.dumps(row, ensure_ascii=False) + "\n")
            else:
                path = stage_dir / f"{name}.json"
                with path.open("w", encoding="utf-8") as f:
                    f.write(json.dumps(payload, ensure_ascii=False, indent=2))
