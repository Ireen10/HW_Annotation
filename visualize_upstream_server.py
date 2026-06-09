"""
Visualizer for HW_Annotation QA upstream artifacts.

Supported sources:
  1. Sharded export bundle: ``{bundle}/jsonl/metadata_*.jsonl`` + ``{bundle}/images/metadata_*.tar``
  2. Merged QA records: ``qa_merged_records.jsonl``
  3. Unrendered QA turns: ``qa_unrendered_records.jsonl``

Usage:
    python visualize_upstream_server.py --data_dir artifacts/pipeline --port 8891
    python visualize_upstream_server.py --data_dir artifacts/pipeline --refined-jsonl artifacts/pipeline/pipeline.example/refine/refine/data.jsonl
"""

from __future__ import annotations

import argparse
import glob
import io
import json
import os
import socket
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template_string, request
from PIL import Image, ImageDraw

from pipeline.export.upstream_read import (
    is_sharded_upstream_root,
    normalize_messages,
    read_jsonl_records,
    read_sharded_upstream,
    resolve_shard_image,
)
from pipeline.viz.mark_render import (
    apply_marks_to_image,
    load_bbox_lookup_from_refined_jsonl,
    pil_to_base64,
)

app = Flask(__name__)
DATA_DIR = "artifacts/pipeline"
IMAGE_ROOT: str | None = None
REFINED_BBOX_LOOKUP: dict[str, dict[str, tuple[float, float, float, float]]] = {}

_SOURCE_CACHE: dict[tuple[str, str, str], dict] = {}


def _coarse_task_key(name: str) -> str:
    return (name or "").strip().lower()


def _families_from_record(rec: dict) -> frozenset[str]:
    families: set[str] = set()
    meta = rec.get("metadata") or {}
    for st in meta.get("source_tasks") or []:
        key = _coarse_task_key(str(st))
        if key:
            families.add(key)
    if not families:
        for turn in meta.get("turns") or []:
            if isinstance(turn, dict):
                key = _coarse_task_key(str(turn.get("task_name") or ""))
                if key:
                    families.add(key)
    if not families and rec.get("sub_task"):
        families.add(_coarse_task_key(str(rec["sub_task"])))
    return frozenset(families)


def _turn_count(rec: dict) -> int:
    meta = rec.get("metadata") or {}
    if meta.get("turn_count"):
        return int(meta["turn_count"])
    turns = _parse_turns(rec)
    return len(turns)


def _parse_turns(rec: dict) -> list[dict[str, str]]:
    if rec.get("sub_task"):
        template = rec.get("template") or {}
        messages = normalize_messages(rec.get("messages"))
        question = ""
        answer = ""
        for msg in messages:
            if msg.get("from") == "human":
                question = str(msg.get("value") or "")
            elif msg.get("from") == "gpt":
                answer = str(msg.get("value") or "")
        return [{
            "task_name": str(rec.get("sub_task") or ""),
            "question": question,
            "answer": answer,
            "template_id": str(template.get("template_id") or ""),
            "instruction_type": str(template.get("answer_instruction_type") or ""),
        }]

    meta = rec.get("metadata") or {}
    turn_meta = meta.get("turns") or []
    messages = normalize_messages(rec.get("messages"))
    out: list[dict[str, str]] = []
    human_idx = 0
    for i, msg in enumerate(messages):
        if msg.get("from") != "human":
            continue
        answer = ""
        if i + 1 < len(messages) and messages[i + 1].get("from") == "gpt":
            answer = str(messages[i + 1].get("value") or "")
        turn_info = turn_meta[human_idx] if human_idx < len(turn_meta) and isinstance(turn_meta[human_idx], dict) else {}
        out.append({
            "task_name": str(turn_info.get("task_name") or ""),
            "question": str(msg.get("value") or ""),
            "answer": answer,
            "template_id": str(turn_info.get("template_id") or ""),
            "instruction_type": "",
        })
        human_idx += 1
    return out


def _mark_spec(rec: dict) -> dict:
    meta = rec.get("metadata") or {}
    if isinstance(meta.get("mark_spec"), dict):
        return meta["mark_spec"]
    if isinstance(rec.get("mark_spec"), dict):
        return rec["mark_spec"]
    return {}


def _mark_slots(rec: dict) -> list[dict[str, str]]:
    mark_spec = _mark_spec(rec)
    slots = mark_spec.get("slots") or []
    out: list[dict[str, str]] = []
    for slot in slots:
        if not isinstance(slot, dict):
            continue
        slot_id = str(slot.get("slot_id") or "")
        out.append({
            "slot_key": slot_id,
            "mark_kind": str(slot.get("mark_kind") or "box"),
            "object_label": str(slot.get("object_label") or ""),
        })
    return out


def discover_sources(data_dir: str) -> list[dict[str, Any]]:
    data_dir = os.path.abspath(data_dir)
    sources: list[dict[str, Any]] = []
    seen: set[str] = set()

    for bundle_jsonl in sorted(glob.glob(os.path.join(data_dir, "**", "bundle", "jsonl", "metadata_*.jsonl"), recursive=True)):
        bundle_root = str(Path(bundle_jsonl).parent.parent)
        if bundle_root in seen:
            continue
        if not is_sharded_upstream_root(bundle_root):
            continue
        seen.add(bundle_root)
        rel = os.path.relpath(bundle_root, data_dir)
        sources.append({
            "label": f"[Export · Sharded] {rel}",
            "path": os.path.join(bundle_root, "jsonl"),
            "kind": "export",
            "bundle_root": bundle_root,
        })

    for merged in sorted(glob.glob(os.path.join(data_dir, "**", "qa_merged_records.jsonl"), recursive=True)):
        merged = os.path.abspath(merged)
        if merged in seen:
            continue
        seen.add(merged)
        rel = os.path.relpath(merged, data_dir)
        sources.append({
            "label": f"[Merged QA] {rel}",
            "path": merged,
            "kind": "merged",
            "bundle_root": None,
        })

    for unrendered in sorted(glob.glob(os.path.join(data_dir, "**", "qa_unrendered_records.jsonl"), recursive=True)):
        unrendered = os.path.abspath(unrendered)
        if unrendered in seen:
            continue
        seen.add(unrendered)
        rel = os.path.relpath(unrendered, data_dir)
        sources.append({
            "label": f"[Unrendered QA] {rel}",
            "path": unrendered,
            "kind": "unrendered",
            "bundle_root": None,
        })

    return sources


def _load_records(path: str, kind: str, bundle_root: str | None) -> list[dict]:
    if kind == "export":
        root = bundle_root or str(Path(path).parent.parent)
        return read_sharded_upstream(root)
    return read_jsonl_records(path)


def _get_source_cache(path: str, kind: str, bundle_root: str | None) -> dict:
    key = (path, kind, bundle_root or "")
    mtime = os.path.getmtime(path if kind != "export" else (bundle_root or path))
    entry = _SOURCE_CACHE.get(key)
    if entry and entry.get("mtime") == mtime:
        return entry
    records = _load_records(path, kind, bundle_root)
    facts = [(_turn_count(rec), _families_from_record(rec)) for rec in records]
    entry = {"mtime": mtime, "records": records, "facts": facts, "total": len(records)}
    _SOURCE_CACHE[key] = entry
    return entry


def _filtered_indices(
    path: str,
    kind: str,
    bundle_root: str | None,
    *,
    filter_task: str = "",
    filter_turns: str = "",
) -> list[int]:
    facts = _get_source_cache(path, kind, bundle_root)["facts"]
    if not filter_task and not filter_turns:
        return list(range(len(facts)))
    out: list[int] = []
    for i, (n_turns, families) in enumerate(facts):
        if filter_turns == "1" and n_turns != 1:
            continue
        if filter_turns == "2" and n_turns != 2:
            continue
        if filter_turns == "3" and n_turns != 3:
            continue
        if filter_turns == "2+" and n_turns < 2:
            continue
        if filter_turns == "3+" and n_turns < 3:
            continue
        task = _coarse_task_key(filter_task)
        if task and task not in families:
            continue
        out.append(i)
    return out


def _collect_task_names(path: str, kind: str, bundle_root: str | None) -> list[str]:
    names: set[str] = set()
    for _, families in _get_source_cache(path, kind, bundle_root)["facts"]:
        names.update(families)
    return sorted(names)


def _resolve_image_ref(image_ref: str) -> Image.Image | None:
    if not image_ref:
        return None
    candidates = [Path(image_ref)]
    if IMAGE_ROOT:
        candidates.append(Path(IMAGE_ROOT) / image_ref)
    for candidate in candidates:
        if candidate.is_file():
            return Image.open(candidate).convert("RGB")
    return None


def _load_display_images(rec: dict, tar_cache: dict) -> list[Image.Image]:
    refs = rec.get("image_refs") or []
    if not isinstance(refs, list):
        refs = [refs]
    images: list[Image.Image] = []
    bundle_root = rec.get("_bundle_root")
    shard_tar = rec.get("_shard_tar")

    if refs:
        for ref in refs:
            img = None
            if bundle_root:
                raw = resolve_shard_image(
                    str(ref),
                    bundle_root=str(bundle_root),
                    shard_tar=str(shard_tar) if shard_tar else None,
                    tar_cache=tar_cache,
                )
                if raw:
                    img = Image.open(io.BytesIO(raw)).convert("RGB")
            if img is None:
                img = _resolve_image_ref(str(ref))
            if img is None:
                frame = Image.new("RGB", (640, 360), (245, 245, 245))
                draw = ImageDraw.Draw(frame)
                draw.multiline_text((16, 16), f"Missing image\n{ref}", fill=(80, 80, 80), spacing=6)
                images.append(frame)
            else:
                images.append(img)
        return images

    image_ref = rec.get("image_ref") or (_mark_spec(rec).get("image_ref"))
    img = _resolve_image_ref(str(image_ref or ""))
    if img is None:
        frame = Image.new("RGB", (640, 360), (245, 245, 245))
        draw = ImageDraw.Draw(frame)
        draw.multiline_text((16, 16), f"Missing image\n{image_ref or '<none>'}", fill=(80, 80, 80), spacing=6)
        return [frame]
    return [img]


def _bbox_lookup_for_record(rec: dict) -> dict[str, tuple[float, float, float, float]] | None:
    item_id = str(rec.get("item_id") or "")
    if item_id and item_id in REFINED_BBOX_LOOKUP:
        return REFINED_BBOX_LOOKUP[item_id]
    return None


def build_display_images(
    rec: dict,
    *,
    slot_ids: list[str] | None,
    marks_mode: str,
    tar_cache: dict,
) -> tuple[list[Image.Image], bool]:
    images = _load_display_images(rec, tar_cache)
    if marks_mode == "off":
        return images, False
    mark_spec = _mark_spec(rec)
    if not mark_spec:
        return images, False
    bbox_lookup = _bbox_lookup_for_record(rec)
    out = [
        apply_marks_to_image(img, mark_spec, slot_ids, bbox_lookup=bbox_lookup)
        for img in images
    ]
    return out, True


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>HW Annotation QA Visualizer</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f0f4f8; color: #333; }
  .header { background: #1b5e20; color: white; padding: 16px 24px; display: flex; align-items: center; gap: 16px; flex-wrap: wrap; position: sticky; top: 0; z-index: 100; }
  .header h1 { font-size: 18px; font-weight: 600; }
  .header select, .header input { padding: 8px 12px; border-radius: 6px; border: none; font-size: 14px; }
  .header select { min-width: 360px; }
  .filters { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
  .filters label { font-size: 12px; }
  .nav button { padding: 6px 14px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.35); background: transparent; color: white; cursor: pointer; }
  .container { max-width: 1200px; margin: 24px auto; padding: 0 24px; }
  .card { background: white; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 20px; }
  .card-header { padding: 12px 18px; background: #e8f5e9; border-bottom: 1px solid #ddd; display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
  .tag { padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; }
  .tag-kind { background: #c8e6c9; color: #1b5e20; }
  .tag-task { background: #bbdefb; color: #0d47a1; }
  .card-body { padding: 18px; }
  .images-row { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 14px; }
  .images-row img { max-height: 380px; border-radius: 8px; border: 1px solid #eee; object-fit: contain; }
  .qa-text { padding: 10px 14px; border-radius: 8px; font-size: 14px; line-height: 1.55; white-space: pre-wrap; margin-top: 6px; }
  .qa-text.q { background: #e3f2fd; }
  .qa-text.a { background: #e8f5e9; }
  .turn-badge { font-size: 11px; background: #fff3e0; color: #e65100; padding: 2px 8px; border-radius: 8px; margin-left: 6px; }
  .mark-panel { margin-bottom: 12px; padding: 10px; background: #fafafa; border-radius: 8px; font-size: 13px; }
  .btn-raw { margin-left: auto; padding: 4px 12px; border: 1px solid #ccc; border-radius: 6px; background: white; cursor: pointer; font-size: 12px; }
  .raw-panel { display: none; margin-top: 12px; padding: 12px; background: #263238; color: #eceff1; border-radius: 8px; font-family: monospace; font-size: 12px; max-height: 420px; overflow: auto; white-space: pre-wrap; }
  .raw-panel.open { display: block; }
  .meta-line { font-size: 12px; color: #666; }
</style>
</head>
<body>
<div class="header">
  <h1>HW Annotation QA Visualizer</h1>
  <select id="sourceSelect" onchange="loadSource()">
    <option value="">-- select source --</option>
    {% for s in sources %}
    <option value="{{ s.path }}|{{ s.kind }}|{{ s.bundle_root or '' }}">{{ s.label }}</option>
    {% endfor %}
  </select>
  <div class="filters">
    <label>Task <select id="filterTask" onchange="applyFilters()"><option value="">All</option></select></label>
    <label>Turns <select id="filterTurns" onchange="applyFilters()">
      <option value="">Any</option><option value="1">1</option><option value="2">2</option>
      <option value="3">3</option><option value="2+">2+</option><option value="3+">3+</option>
    </select></label>
  </div>
  <div class="nav">
    <button onclick="navigate(-1)">Prev</button>
    <span id="pageInfo">-</span>
    <button onclick="navigate(1)">Next</button>
  </div>
</div>
<div class="container" id="cards"></div>
<script>
let currentPath='', currentKind='', bundleRoot='', currentPage=0, totalRows=0, filteredTotal=0;
const pageSize=6;
function parseSelectVal(){const v=document.getElementById('sourceSelect').value;if(!v)return;const i1=v.indexOf('|'),i2=v.indexOf('|',i1+1);currentPath=v.slice(0,i1);currentKind=v.slice(i1+1,i2);bundleRoot=v.slice(i2+1);}
function loadSource(){parseSelectVal();currentPage=0;if(!currentPath)return;fetch('/api/filter_options?path='+encodeURIComponent(currentPath)+'&kind='+currentKind+'&bundle_root='+encodeURIComponent(bundleRoot)).then(r=>r.json()).then(d=>{const sel=document.getElementById('filterTask');sel.innerHTML='<option value="">All</option>'+(d.tasks||[]).map(t=>`<option value="${t}">${t}</option>`).join('');fetchPage();});}
function applyFilters(){currentPage=0;fetchPage();}
function fetchPage(){const p=new URLSearchParams({path:currentPath,kind:currentKind,bundle_root:bundleRoot,page:String(currentPage),page_size:String(pageSize)});const ft=document.getElementById('filterTask').value,fn=document.getElementById('filterTurns').value;if(ft)p.set('filter_task',ft);if(fn)p.set('filter_turns',fn);fetch('/api/data?'+p).then(r=>r.json()).then(d=>{totalRows=d.total;filteredTotal=d.filtered_total;document.getElementById('cards').innerHTML=(d.rows||[]).map(cardHtml).join('');updateNav();});}
function updateNav(){const start=filteredTotal?currentPage*pageSize+1:0;const end=Math.min((currentPage+1)*pageSize,filteredTotal);document.getElementById('pageInfo').textContent=`rows ${start}-${end} / ${filteredTotal}`;}
function navigate(d){const maxPage=Math.max(0,Math.ceil(filteredTotal/pageSize)-1);currentPage=Math.max(0,Math.min(maxPage,currentPage+d));fetchPage();}
function cardHtml(r){const tasks=(r.source_tasks||[]).join(', ');const imgs=(r.display_images||[]).map(src=>`<img src="${src}" alt="">`).join('');const turns=(r.turns||[]).map((t,i)=>`<div><span class="turn-badge">Turn ${i+1} · ${t.task_name||''}</span><div class="qa-text q">${escapeHtml(t.question||'')}</div><div class="qa-text a">${escapeHtml(t.answer||'')}</div></div>`).join('');return `<div class="card"><div class="card-header"><span class="tag tag-kind">${r.kind}</span><span class="tag tag-task">${escapeHtml(tasks)}</span><span class="meta-line">sample_id: ${escapeHtml(r.sample_id||'')}</span><button class="btn-raw" onclick="toggleRaw(${r.row_index}, this)">Raw</button></div><div class="card-body"><div class="images-row">${imgs}</div>${turns}<pre class="raw-panel" id="raw-${r.row_index}"></pre></div></div>`;}
function toggleRaw(idx,btn){const p=document.getElementById('raw-'+idx);if(p.classList.contains('open')){p.classList.remove('open');btn.textContent='Raw';return;}btn.textContent='Hide';p.classList.add('open');fetch(`/api/raw_row?path=${encodeURIComponent(currentPath)}&kind=${currentKind}&bundle_root=${encodeURIComponent(bundleRoot)}&index=${idx}`).then(r=>r.json()).then(d=>{p.textContent=JSON.stringify(d.row,null,2);});}
function escapeHtml(t){const d=document.createElement('div');d.textContent=t==null?'':String(t);return d.innerHTML;}
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE, sources=discover_sources(DATA_DIR))


@app.route("/api/filter_options")
def api_filter_options():
    path = request.args.get("path", "")
    kind = request.args.get("kind", "merged")
    bundle_root = request.args.get("bundle_root") or None
    return jsonify({"tasks": _collect_task_names(path, kind, bundle_root)})


@app.route("/api/data")
def api_data():
    path = request.args.get("path", "")
    kind = request.args.get("kind", "merged")
    bundle_root = request.args.get("bundle_root") or None
    page = int(request.args.get("page", 0))
    page_size = int(request.args.get("page_size", 6))
    filter_task = request.args.get("filter_task", "")
    filter_turns = request.args.get("filter_turns", "")

    cache = _get_source_cache(path, kind, bundle_root)
    indices = _filtered_indices(path, kind, bundle_root, filter_task=filter_task, filter_turns=filter_turns)
    page_indices = indices[page * page_size : (page + 1) * page_size]
    tar_cache: dict = {}
    rows_out = []
    for i in page_indices:
        rec = cache["records"][i]
        images, marks_applied = build_display_images(rec, slot_ids=None, marks_mode="all", tar_cache=tar_cache)
        meta = rec.get("metadata") or {}
        rows_out.append({
            "row_index": i,
            "kind": kind,
            "sample_id": rec.get("sample_id") or rec.get("item_id"),
            "source_tasks": meta.get("source_tasks") or ([rec.get("sub_task")] if rec.get("sub_task") else []),
            "turns": _parse_turns(rec),
            "display_images": [pil_to_base64(img) for img in images],
            "marks_overlay_applied": marks_applied,
        })
    if "tar" in tar_cache:
        tar_cache["tar"].close()
    return jsonify({
        "total": cache["total"],
        "filtered_total": len(indices),
        "page": page,
        "rows": rows_out,
    })


@app.route("/api/raw_row")
def api_raw_row():
    path = request.args.get("path", "")
    kind = request.args.get("kind", "merged")
    bundle_root = request.args.get("bundle_root") or None
    index = int(request.args.get("index", 0))
    cache = _get_source_cache(path, kind, bundle_root)
    if index < 0 or index >= cache["total"]:
        return jsonify({"row": {}})
    return jsonify({"row": cache["records"][index]})


def _print_listen_info(host: str, port: int) -> None:
    print(f"\nListening on http://{host}:{port}")
    print(f"  Local: http://127.0.0.1:{port}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HW Annotation QA / export visualizer")
    parser.add_argument("--port", type=int, default=8891)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--data_dir", type=str, default="artifacts/pipeline")
    parser.add_argument("--image-root", type=str, default=None, help="Fallback root for image_ref paths")
    parser.add_argument(
        "--refined-jsonl",
        type=str,
        default=None,
        help="Refined data.jsonl used to draw bbox marks by item_id/object_id",
    )
    args = parser.parse_args()

    DATA_DIR = args.data_dir
    IMAGE_ROOT = args.image_root
    if args.refined_jsonl:
        REFINED_BBOX_LOOKUP.update(load_bbox_lookup_from_refined_jsonl(args.refined_jsonl))

    sources = discover_sources(DATA_DIR)
    print(f"Found {len(sources)} sources in {DATA_DIR}:")
    for s in sources:
        print(f"  {s['label']}")
    _print_listen_info(args.host, args.port)
    app.run(host=args.host, port=args.port, debug=False)
