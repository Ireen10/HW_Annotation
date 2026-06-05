"""CLI: python -m pipeline  (optional JSONL export after refine)"""

from __future__ import annotations

import argparse
import json
from dataclasses import replace

from pipeline.config import LLMSettings, RefineConfig
from pipeline.refine.export import export_samples_jsonl
from pipeline.runtime import (
    build_default_pipeline_spec,
    load_pipeline_spec,
    run_pipeline,
)


def _merge_refine_overrides(base: dict[str, object], args: argparse.Namespace) -> dict[str, object]:
    merged = dict(base)
    if args.no_llm:
        merged["use_llm"] = False
    if args.no_strict:
        merged["strict_validation"] = False
    if args.llm_base_url is not None:
        merged["llm_base_url"] = args.llm_base_url
    if args.llm_model is not None:
        merged["llm_model"] = args.llm_model
    if args.limit is not None:
        merged["limit"] = args.limit
    if args.workers is not None:
        merged["workers"] = args.workers
    if args.fail_fast:
        merged["fail_fast"] = True
    return merged


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run stage-based annotation pipeline")
    parser.add_argument("-i", "--input", default=None)
    parser.add_argument("-o", "--output", default=None, help="Optional JSONL export path")
    parser.add_argument("--pipeline-config", default=None, help="JSON/YAML pipeline config path")
    parser.add_argument(
        "--artifacts-dir",
        default="artifacts/pipeline",
        help="Root directory for stage artifacts",
    )
    parser.add_argument(
        "--from-stage",
        default=None,
        help="Resume execution from this stage name (loads previous stage artifact)",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Disable artifact resume and force stage re-run",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process only the first N samples for quick debugging",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of parallel workers for sample-level refine",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop immediately on the first failed sample",
    )
    parser.add_argument("--no-llm", action="store_true")
    parser.add_argument("--no-strict", action="store_true", help="Keep invalid refined samples with notes")
    parser.add_argument("--llm-base-url", default=None)
    parser.add_argument("--llm-model", default=None)
    args = parser.parse_args(argv)

    cfg = RefineConfig()
    if args.no_llm:
        cfg = replace(cfg, use_llm=False)
    if args.no_strict:
        cfg = replace(cfg, strict_validation=False)
    if args.llm_base_url or args.llm_model:
        llm = cfg.llm
        cfg = replace(
            cfg,
            llm=LLMSettings(
                base_url=args.llm_base_url or llm.base_url,
                model=args.llm_model or llm.model,
                api_key=llm.api_key,
                timeout_s=llm.timeout_s,
                temperature=llm.temperature,
            ),
        )

    if args.pipeline_config:
        spec = load_pipeline_spec(args.pipeline_config)
        if args.input is not None:
            spec = replace(spec, input_path=args.input)
        if args.artifacts_dir:
            spec = replace(spec, artifacts_dir=args.artifacts_dir)
        spec = replace(
            spec,
            stages=tuple(
                replace(stage, params=_merge_refine_overrides(stage.params, args))
                if stage.kind == "refine"
                else stage
                for stage in spec.stages
            ),
        )
        if args.no_resume:
            spec = replace(
                spec,
                stages=tuple(replace(stage, resume=False) for stage in spec.stages),
            )
    else:
        stage_params = {
            "use_llm": cfg.use_llm,
            "strict_validation": cfg.strict_validation,
            "llm_base_url": cfg.llm.base_url,
            "llm_model": cfg.llm.model,
            "limit": args.limit,
            "workers": args.workers,
            "fail_fast": args.fail_fast,
        }
        spec = build_default_pipeline_spec(
            input_path=args.input or "samples/samples.jsonl",
            artifacts_dir=args.artifacts_dir,
            refine_params=stage_params,
        )
        if args.no_resume:
            spec = replace(
                spec,
                stages=tuple(replace(stage, resume=False) for stage in spec.stages),
            )

    result = run_pipeline(spec, from_stage=args.from_stage)
    refined = list(result.samples)

    exported = 0
    if args.output:
        exported = export_samples_jsonl(refined, args.output, total=len(refined))

    summary = {
        "input": str(spec.input_path),
        "refined_count": len(refined),
        "exported": exported,
        "export_path": args.output,
        "load_errors": list(result.load_errors),
        "stage_count": len(result.stages),
        "stages": [
            {
                "name": s.name,
                "kind": s.kind,
                "output_path": s.output_path,
                "input_count": s.input_count,
                "output_count": s.output_count,
                "resumed": s.resumed,
                "failed_count": s.failed_count,
            }
            for s in result.stages
        ],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
