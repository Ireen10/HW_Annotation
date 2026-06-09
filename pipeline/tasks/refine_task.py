"""Refine stage task implementation."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from hw_annotation import parse_sample_dict
from pipeline.base_task import BaseTask, TaskRunResult
from pipeline.config import LLMSettings, RefineConfig
from pipeline.refine import refine_sample
from pipeline.utils.llm import OpenAICompatibleClient
from tqdm.auto import tqdm


class RefineTask(BaseTask):
    incremental_resume_capable = True

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
        workers = int(params.get("workers", 1))
        if workers < 1:
            raise ValueError(f"workers must be >= 1, got {workers}")

        limit = params.get("limit")
        if limit is not None:
            limit = int(limit)
            if limit < 0:
                raise ValueError(f"limit must be >= 0, got {limit}")
        fail_fast = bool(params.get("fail_fast", False))

        stage_output_dir = self.runtime_context.get("stage_output_dir")
        if not stage_output_dir:
            raise ValueError("missing runtime_context.stage_output_dir for refine output")
        output_path = Path(stage_output_dir) / "data.jsonl"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        resume_requested = bool(self.runtime_context.get("resume_requested", False))

        existing_samples: list = []
        existing_ids: set[str] = set()
        if resume_requested and output_path.is_file():
            existing_samples = _load_existing_samples(output_path)
            existing_ids = {s.item_id for s in existing_samples}

        selected = list(samples if limit is None else samples[:limit])
        refined: list = list(existing_samples)
        pending = [s for s in selected if s.item_id not in existing_ids]
        open_mode = "a" if (resume_requested and output_path.is_file()) else "w"
        with output_path.open(open_mode, encoding="utf-8") as f:
            if workers == 1:
                iterator = tqdm(pending, total=len(pending), desc="Refining samples")
                for sample in iterator:
                    try:
                        row = refine_sample(sample, client=client, config=refine_cfg)
                        refined.append(row)
                        f.write(json.dumps(row.to_dict(), ensure_ascii=False) + "\n")
                        f.flush()
                    except Exception as exc:  # noqa: BLE001
                        if fail_fast:
                            raise
                        errors.append(f"{sample.item_id}: {exc}")
            else:
                from concurrent.futures import ThreadPoolExecutor, as_completed

                with ThreadPoolExecutor(max_workers=workers) as ex:
                    future_to_sample = {
                        ex.submit(refine_sample, sample, client=client, config=refine_cfg): sample
                        for sample in pending
                    }
                    for future in tqdm(as_completed(future_to_sample), total=len(pending), desc="Refining samples"):
                        sample = future_to_sample[future]
                        try:
                            row = future.result()
                            refined.append(row)
                            f.write(json.dumps(row.to_dict(), ensure_ascii=False) + "\n")
                            f.flush()
                        except Exception as exc:  # noqa: BLE001
                            if fail_fast:
                                raise
                            errors.append(f"{sample.item_id}: {exc}")

        return TaskRunResult(
            samples=tuple(refined),
            failed_count=len(errors),
            wrote_main_output=True,
        )


def _load_existing_samples(path: Path) -> list:
    rows: list = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                payload = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON while resuming refine: {exc}") from exc
            rows.append(parse_sample_dict(payload))
    return rows
