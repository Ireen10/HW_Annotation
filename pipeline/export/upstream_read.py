"""Read sharded upstream export bundles (JSONL + tar)."""

from __future__ import annotations

import json
import tarfile
from pathlib import Path

JSONL_SUBDIR = "jsonl"
IMAGES_SUBDIR = "images"
DATASET_METADATA_FILENAME = "metadata.json"


def is_sharded_upstream_root(export_root: str | Path) -> bool:
    return (Path(export_root) / JSONL_SUBDIR).is_dir()


def discover_shard_pairs(export_root: str | Path) -> list[tuple[Path, Path | None]]:
    root = Path(export_root)
    jsonl_dir = root / JSONL_SUBDIR
    images_dir = root / IMAGES_SUBDIR
    if not jsonl_dir.is_dir():
        return []
    pairs: list[tuple[Path, Path | None]] = []
    for jf in sorted(jsonl_dir.glob("metadata_*.jsonl")):
        tar = images_dir / f"{jf.stem}.tar"
        pairs.append((jf, tar if tar.is_file() else None))
    return pairs


def read_jsonl_records(path: str | Path) -> list[dict]:
    rows: list[dict] = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            text = line.strip()
            if not text:
                continue
            rows.append(json.loads(text))
    return rows


def read_sharded_upstream(export_root: str | Path) -> list[dict]:
    root = Path(export_root)
    records: list[dict] = []
    for jf, tar in discover_shard_pairs(root):
        for rec in read_jsonl_records(jf):
            row = dict(rec)
            row["_bundle_root"] = str(root)
            if tar is not None:
                row["_shard_tar"] = str(tar)
            records.append(row)
    return records


def resolve_shard_image(
    ref: str,
    *,
    bundle_root: str,
    shard_tar: str | None,
    tar_cache: dict,
) -> bytes | None:
    ref = str(ref).replace("\\", "/")
    local = Path(bundle_root) / ref
    if local.is_file():
        return local.read_bytes()

    if not shard_tar:
        return None

    tar_path = shard_tar
    if tar_cache.get("tar_path") != tar_path:
        if "tar" in tar_cache:
            tar_cache["tar"].close()
        tar_cache["tar_path"] = tar_path
        tar_cache["tar"] = tarfile.open(tar_path, "r")
        tar_cache["members"] = {m.name: m for m in tar_cache["tar"].getmembers()}

    member = tar_cache["members"].get(ref)
    if member is None:
        return None
    extracted = tar_cache["tar"].extractfile(member)
    if extracted is None:
        return None
    return extracted.read()


def normalize_messages(raw: object) -> list[dict]:
    if not isinstance(raw, list):
        return []
    if len(raw) == 1 and isinstance(raw[0], list):
        inner = raw[0]
        if inner and isinstance(inner[0], dict) and "from" in inner[0]:
            return inner
    if raw and isinstance(raw[0], dict) and "from" in raw[0]:
        return raw
    return raw
