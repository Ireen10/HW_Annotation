"""CLI: python -m pipeline  (optional JSONL export after refine)"""

from __future__ import annotations

import argparse
import json
from dataclasses import replace

from pipeline.config import LLMSettings, RefineConfig
from pipeline.refine.export import export_samples_jsonl
from pipeline.refine.run import refine_dataset


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Refine annotations (primary output: in-memory samples)")
    parser.add_argument("-i", "--input", default="samples/samples.jsonl")
    parser.add_argument("-o", "--output", default=None, help="Optional JSONL export path")
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

    from hw_annotation import HwAnnotationDataset

    ds = HwAnnotationDataset(args.input, status_filter=None)
    client = None
    if cfg.use_llm:
        from pipeline.utils.llm import OpenAICompatibleClient

        client = OpenAICompatibleClient(cfg.llm)

    refine_errors: list[str] = []
    refined = refine_dataset(
        ds,
        client=client,
        config=cfg,
        limit=args.limit,
        workers=args.workers,
        skip_errors=not args.fail_fast,
        errors=refine_errors,
    )
    exported = 0
    if args.output:
        exported = export_samples_jsonl(refined, args.output, total=len(refined))

    summary = {
        "input": str(args.input),
        "refined_count": len(refined),
        "exported": exported,
        "export_path": args.output,
        "load_errors": ds.load_errors,
        "llm_enabled": cfg.use_llm,
        "strict_validation": cfg.strict_validation,
        "limit": args.limit,
        "workers": args.workers,
        "failed_count": len(refine_errors),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if refine_errors:
        print("failed_samples:")
        for err in refine_errors:
            print(f"  {err}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
