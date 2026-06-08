"""Refine stage task implementation."""

from __future__ import annotations

from dataclasses import replace

from pipeline.base_task import BaseTask, TaskRunResult
from pipeline.config import LLMSettings, RefineConfig
from pipeline.refine import refine_dataset
from pipeline.utils.llm import OpenAICompatibleClient


class RefineTask(BaseTask):
    def run(self, samples: tuple) -> TaskRunResult:
        params = self.params
        llm_cfg = LLMSettings.from_env()
        llm_cfg = replace(
            llm_cfg,
            base_url=str(params.get("llm_base_url") or llm_cfg.base_url),
            model=str(params.get("llm_model") or llm_cfg.model),
            api_key=str(params.get("llm_api_key") or llm_cfg.api_key),
            timeout_s=float(params.get("llm_timeout_s") or llm_cfg.timeout_s),
            temperature=float(params.get("llm_temperature") or llm_cfg.temperature),
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
            samples,
            client=client,
            config=refine_cfg,
            limit=params.get("limit"),
            workers=int(params.get("workers", 1)),
            skip_errors=not bool(params.get("fail_fast", False)),
            errors=errors,
        )
        return TaskRunResult(samples=tuple(refined), failed_count=len(errors))
