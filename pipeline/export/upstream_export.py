"""Sharded JSONL + tar export for merged QA samples."""

from __future__ import annotations

import json
import os
import tarfile
from pathlib import Path


DEFAULT_SHARD_SIZE = 8192


def write_sharded_bundle(
    records: list[dict],
    *,
    output_root: str,
    shard_size: int = DEFAULT_SHARD_SIZE,
    image_root: str | None = None,
) -> dict[str, object]:
    if shard_size <= 0:
        raise ValueError(f"shard_size must be > 0, got {shard_size}")

    root = Path(output_root)
    jsonl_dir = root / "jsonl"
    image_dir = root / "images"
    jsonl_dir.mkdir(parents=True, exist_ok=True)
    image_dir.mkdir(parents=True, exist_ok=True)

    shard_count = 0
    total_records = 0
    total_images = 0

    for start in range(0, len(records), shard_size):
        shard = records[start : start + shard_size]
        shard_name = f"metadata_{shard_count:06d}"
        jsonl_path = jsonl_dir / f"{shard_name}.jsonl"
        tar_path = image_dir / f"{shard_name}.tar"

        tar_members_written = 0
        with jsonl_path.open("w", encoding="utf-8") as jf, tarfile.open(tar_path, "w") as tf:
            for row in shard:
                packed = dict(row)
                packed["image_refs"] = []
                image_ref = row.get("image_ref")
                if isinstance(image_ref, str) and image_ref:
                    source_path = _resolve_image_path(image_ref, image_root)
                    if source_path is not None and source_path.is_file():
                        member = f"images/{row.get('sample_id', 'unknown')}/00{source_path.suffix or '.jpg'}"
                        tf.add(str(source_path), arcname=member)
                        packed["image_refs"].append(member)
                        tar_members_written += 1
                jf.write(json.dumps(packed, ensure_ascii=False) + "\n")

        total_images += tar_members_written
        total_records += len(shard)
        shard_count += 1

    metadata = {
        "schema_version": "1.0",
        "shard_size": shard_size,
        "total_records": total_records,
        "total_image_members": total_images,
        "shard_count": shard_count,
    }
    (root / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return metadata


def _resolve_image_path(image_ref: str, image_root: str | None) -> Path | None:
    p = Path(image_ref)
    if p.is_file():
        return p
    if image_root:
        alt = Path(image_root) / image_ref
        if alt.is_file():
            return alt
    return None
